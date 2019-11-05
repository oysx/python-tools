#!/usr/bin/env python
import json, math, sys, copy
from bokeh.plotting import figure, output_file, show, save
from bokeh.models.layouts import Column, Row
import numpy as np
import datetime

filename = sys.argv[1]
file = open(filename, 'r')
lines = file.readlines()
    
print len(lines)

def doMap(data, maps=None):
    if maps:
        return maps[data]

    result = -1
    if data == "/ak1.php":
        result = 1
    elif data == "/ak2.php":
        result = 2
    elif data == "/tt.ajax":
        result = 3
    elif data == "/detail.php":
        result = 4
    elif data == "/detail2.php":
        result = 5
    elif data == "/trans1.php":
        result = 6
    elif data == "/t2.ajax":
        result = 7
    elif data == "/trans2.php":
        result = 8
    elif data == "/query.json":
        result = 9
    elif data == "/":
        result = 10

    return result

def uniqField(lines, field, condition=None, callback=None):
    result = []
    for l in lines:
        data = json.loads(l)
        if data.get("result"):
            data = data["result"]
            if data.get(field):
                if condition:
                    # print condition.keys()[0], condition.values()[0]
                    if data.get(condition.keys()[0]) != condition.values()[0]:
                        continue
                
                f = data[field]
                try:
                    result.index(f)
                except Exception as e:
                    result += [f]
                if callback:
                    func = callback["func"]
                    para = callback["para"]
                    ret = callback.get("result")
                    if not ret:
                        callback["result"] = {}
                    ret = callback["result"]
                    ret[f] = func(data, para, ret.get(f))
    return result

def countField(data, para, result):
    if not result:
        result = {}

    field = para["field"]
    ret = data.get(field)
    if ret:
        if not result.get(ret):
            result[ret] = 0
        result[ret] += 1

    return result

def createMap(lists, output=None):
    result = {}
    lists.sort()
    for i in range(len(lists)):
        result[lists[i]] = i+1

    if output:
        f = json.dumps(result)
        fd = open(output, "w")
        fd.write(f)
        fd.close()

    return result

requestType = {
    "initiator": 0,
    "follower" : 1,
    "resource" : 2,
}

class requestEntity(object):
    def __init__(self, data, key):
        self.data = data
        self.key = key
        self.logicalFinder = []
        self.follower = {}
        self.children = []
        self.type = None

    def addLogicalFinder(self, finder):
        self.logicalFinder += [finder]
    
    def addFollower(self, key, entity):
        if self.follower.get(key) == None:
            self.follower[key] = {}
        self.follower[key] = entity

    def setType(self, value):
        self.type = value

    def addChild(self, entity):
        self.children += [entity]
        
    def findFollower(self, entities):
        followers = []
        for entity in entities:
            if self.logicalFinder[0].find(self.data, entity.data):
                self.addFollower(entity.data.get(self.key), entity)
                followers += [entity]
        return followers

class pathEntity(requestEntity):
    def __init__(self, data):
        super(pathEntity, self).__init__(data, "path")
        self.initiator = ["/ak1.php", "/detail.php", "/trans1.php", "/trans2.php"]
        self.others = [""]
        self.finder = referSearch()

        self.detectType()
        self.addLogicalFinder(self.finder)

    def detectType(self):
        if self.data.get(self.key) in self.initiator:
            self.setType("initiator")
        elif self.data.get(self.key) in self.others:
            self.setType("follower")

class relationSearch(object):
    def __init__(self, pair):
        self.key = pair.keys()[0]
        self.value = pair.values()[0]
    
    def find(self, base, derived):
        if base.get(self.key) == derived.get(self.value):
            return True
        return False

class referSearch(relationSearch):
    def __init__(self):
        pair = {"args_encrypted" : "referer"}
        super(referSearch, self).__init__(pair)
    
    def find(self, base, derived):
        if type(base.get(self.key)) == str or type(base.get(self.key)) == unicode:
            if True:
            # if base.get(self.key).startswith(u"?y7bRbp=") or base.get(self.key).startswith(u"?MmEwMD=") \
            # or base.get(self.key).startswith(u"?request:tid="):
                # return derived.get(self.value).endswith(base.get(self.key))
                return derived.get(self.value) == "http://" + base.get("hostname").split(":")[0] + base.get("path") + base.get(self.key)
        return False

def logicalSearch(jsons):
    entities = []
    for data in jsons:
        entities += [pathEntity(data)]

    followers = []
    for i in range(len(entities)):
        followers += entities[i].findFollower(entities[i+1:])

    result = []
    for entity in entities:
        if entity in followers:
            continue
        result += [entity]

    return result
        
def getDeltaValue(group, field):
    result = []
    prev = None
    for cur in group:
        if not prev:
            result += [0.0]
        else:
            result += [float(cur[field] - prev[field])]
        prev = cur
    # print group
    # print result
    return result

def fft(data, sample_period, power=False, use_db=True):
    dt = sample_period
    sp = np.fft.rfft(data)
    if power:
        spectrum = (np.abs(sp) * 2 * dt) ** 2
    else: 
        spectrum = np.abs(sp)# * 2 * dt
        
    if use_db:
        max_input = np.max(data)
        if power:
            spectrum = 20 * np.log10(spectrum / max_input)
        else:
            spectrum = 10 * np.log10(spectrum / max_input)
    n = len(data)
    freqs = np.fft.fftfreq(n, sample_period)
    # Ignore the negative part of frequency. It's because of symmetry of FFT.
    idx = np.argsort(freqs)
    idx = filter(lambda i: freqs[i] > 0, idx)
    
    return freqs[idx], spectrum[idx].real

def drawFreq(data):
    freqs, spectrum = fft(data, len(data), use_db=False)

    p = figure(width=800, height=300, title="FFT",
        x_axis_label="Frequency(Hz)", y_axis_label="Amplitude",
        )
    tmp = getDeltaValue([ {"x": i}for i in freqs], "x")
    p.vbar(x=freqs, top=spectrum, color="blue", width=min(tmp))
    show(p)

def drawChart(lines, maps):
    y = []
    x = []
    y1 = []
    y2 = []
    y3 = []
    timebase = None
    for content in lines:
        data = json.loads(content)
        if data.get("result"):
            data = data["result"]
        # if data.get("id"):
        #     x += [data["timestamp"]]
        #     y += [1]
        if data.get("path"):
            if timebase == None:
                timebase = long(data["timestamp"])
            x += [(long(data["timestamp"])-timebase)/1000]
            y += [doMap(data["path"], maps)]
            # if data["cookie"]=="188995515619362":
            #     y1 += [doMap(data["path"], maps)]
            # else:
            #     y1 += [0]
            # if data["cookie"]=="195764856981744":
            #     y2 += [doMap(data["path"], maps)]
            # else:
            #     y2 += [0]
            y1 += [7 if data.get("id")=="9999" else 0]
            y2 += [8 if data.get("id")=="1000" else 0]
            y3 += [9 if data.get("id")=="8822" else 0]

    drawFreq(y)

    print len(x)
    p = figure(width=800, height=600)
    p.line(x, y, line_width=2)
    p.circle(x, y, size=8)
    p.circle(x, y1, size=8, color="blue")
    p.circle(x, y2, size=8, color="green")
    p.circle(x, y3, size=8, color="red")

    output_file(sys.argv[1]+".html")
    show(p)

def findPure9999(lines):
    result = {"func": countField, "para": {"field": "id"},}
    ids=uniqField(lines, "cookieUniq", {"mobile": "true"}, result)
    print len(ids)
    data = result.get("result")
    for k in data:
        if data[k].get("9999") or data[k].get("1001"):
            continue
        
        print k,data[k]

def drawPath(lines):
    path=uniqField(lines, "path")
    print "path count:" , len(path)
    path=createMap(path, sys.argv[1]+".map")
    drawChart(lines, path)

def findReferer(lines):
    result = getRecords(lines)
    result = logicalSearch(result)
    print len(result)

    for entity in result:
        # if entity.type == "initiator":
        if entity.follower and len(entity.follower) > 0:
            print entity.data.get(entity.key), ":", entity.data.get("cookie")
            for i in entity.follower:
                print "\t>>>", i, ": ", entity.follower[i].data.get("cookie")

def getRecords(lines):
    result = []
    for l in lines:
        data = json.loads(l)
        if data.get("result"):
            data = data.get("result")
            result += [data]

    result.reverse()
    print len(result)
    return result

def calDeltaValue(records, fields):
    olds = {}
    for e in records:
        output = ""
        for f in fields:
            old = olds.get(f)
            new = e.get(f)
            if not new:
                continue
            if old:
                delta = int(new) - int(old)
                output += f + ":" + str(delta) + "\t"
            olds[f] = new
        
        print output

start = datetime.datetime.now()
# findPure9999(lines)
# drawPath(lines)
# findReferer(lines)
calDeltaValue(getRecords(lines), ["input_analyze_captcha_timestamp"])
end = datetime.datetime.now()
print end-start, "seconds"
