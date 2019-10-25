#!/usr/bin/env python
import json, math, sys, copy
from bokeh.plotting import figure, output_file, show, save
from bokeh.models.layouts import Column, Row

filename = sys.argv[1]
file = open(filename, 'r')
lines = file.readlines()
    
print len(lines)

def MathVectorTheta(group):
    i = 0
    while i<len(group):
        if group[i]["x"] == 0:
            group[i]["theta"] =  90 if group[i]["y"] > 0 else -90 if group[i]["y"] < 0 else group[i-1]["theta"] if i>=1 else 0
        else:
            group[i]["theta"] = math.atan(group[i]["y"] / group[i]["x"])
            group[i]["theta"] = group[i]["theta"] * 180 / math.pi
            if group[i]["y"] < 0 and group[i]["x"] < 0:
                group[i]["theta"] -= 180
            elif group[i]["y"] > 0 and group[i]["x"] < 0:
                group[i]["theta"] += 180
            
        group[i]["distance"] = math.sqrt(group[i]["x"] * group[i]["x"] + group[i]["y"] * group[i]["y"]);

        group[i]["distance"] = round(group[i]["distance"] * 10000);
        group[i]["theta"] = round(group[i]["theta"]);
        i += 1

def PhysAcceleration(displacement):
    displacement = MathDerivativeMatrix(displacement)
    return MathDerivativeMatrix(displacement)


def PhysVelocity(displacement):
    return MathDerivativeMatrix(displacement)

def MathDerivativeMatrix(group, dx="x", dy="y"):
    result = []
    i = 1
    pre = 0
    while i < len(group):
        rec = MathDerivativeDimension(group[pre], group[i], dx, dy)
        if rec == None:
            i += 1
            continue
        pre = i
        result.append(rec)
        i += 1

    return result

def MathDerivativeDimension(preElement, curElement, dx="x", dy="y"):
    result = {}
    deltaTime = curElement["t"] - preElement["t"]
    if deltaTime <= 0:
        return None

    deltaTime = float(deltaTime)
    result["t"] = curElement["t"]
    result[dx] = (curElement[dx] - preElement[dx]) / deltaTime
    result[dy] = (curElement[dy] - preElement[dy]) / deltaTime

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

def prepareTimeStamp(group):
    i = len(group) - 1
    while i > 0:
        group[i]["dt"] = float(group[i]["t"] - group[i-1]["t"])
        i -= 1
    group[0]["dt"] = 0

def calculateVelocity(group):
    prepareTimeStamp(group)

    result = []
    rec = {}
    i = 1
    while i < len(group):
        if group[i]["dt"] == 0:
            i += 1
            continue
        rec["dt"] = group[i]["dt"]
        rec["dx"] = (group[i]["x"] - group[i-1]["x"]) / group[i]["dt"]
        rec["dy"] = (group[i]["y"] - group[i-1]["y"]) / group[i]["dt"]
        result.append(rec)
        rec = {}
        i += 1

    return result

def calculateAcceleration(group):
    v = calculateVelocity(group)
    result = []
    rec = {}
    i = 1
    while i < len(v):
        deltaTime = (v[i]["dt"] + v[i-1]["dt"]) / 2
        rec["t"] = deltaTime
        rec["x"] = (v[i]["dx"] - v[i-1]["dx"]) / deltaTime
        rec["y"] = (v[i]["dy"] - v[i-1]["dy"]) / deltaTime
        result.append(rec)
        rec = {}
        i += 1

    MathVectorTheta(result)
    return result

def getAccelerationRecords(records):
    acceleration = PhysAcceleration(records)
    MathVectorTheta(acceleration)
    return acceleration

def getVelocityRecords(records):
    velocity = PhysVelocity(records)
    MathVectorTheta(velocity)
    return velocity

def getVelocityRateRecords(records):
    result = getVelocityRecords(records)
    return MathDerivativeMatrix(result, "theta", "distance")

def getPointRecords(records):
    return records

def drawXYPoint(ix, iy, entry, para="+"):
    return entry["x"], entry["y"] if para=="+" else -entry["y"], "x", "y"

def drawORPoint(ix, iy, entry, para):
    ix += entry["distance"] * math.cos(entry["theta"] * math.pi / 180)
    iy += entry["distance"] * math.sin(entry["theta"] * math.pi / 180)
    return ix, iy, "x", "y"

def drawWaveAt(ix, iy, entry, field):
    return entry["t"], entry[field], "time", field

def drawWaveDt(ix, iy, entry, field):
    return ix + entry["t"], entry[field], "time", field

### data analysis start ###

import numpy as np
def MathOutlierDetectorByMedian(signal, threshold = 3):
    """
    signal: data list[]
    returns: outlier list[] 
    """
    signal = np.asanyarray(signal)
    difference = np.abs(signal - np.median(signal))
    median_difference = np.median(difference)
    if median_difference == 0:
        median_difference = 1.0
    s = 0 if median_difference == 0 else difference / float(median_difference)
    mask = s > threshold
    return [i for i in range(len(signal)) if mask.tolist()[i]==True]

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

### data analysis end ###

def MathRelativeValue(data):
    preEntry = None
    for entry in data:
        saveEntry = entry.copy()

        for field in entry:
            entry[field] = entry[field] - preEntry[field] if preEntry else 0

        if not preEntry:
            preEntry = saveEntry

def MathCompensatePoint(data):
    result = []
    content = {}
    preEntry = None
    for entry in data:
        if preEntry:
            deltaTime = entry["t"] - preEntry["t"]
            for i in range(deltaTime):
                content = {}
                for field in entry:
                    delta = (entry[field] - preEntry[field]) * i / deltaTime
                    content[field] = preEntry[field] + delta
                result.append(content)

        result.append(entry)
        preEntry = entry

    return result

def MathVarietyRatio(data):
    result = list(set(data))
    return len(result) / float(len(data))

def shortMovementDetector(data, threshold):
    x = [entry["x"] for entry in data]
    y = [entry["y"] for entry in data]
    x = max(x) - min(x)
    y = max(y) - min(y)
    return math.sqrt(x*x + y*y) / threshold

def shortCountSkip(data):
    return len(data) <= 3
    
def splitData(data):
    if shortCountSkip(data):
        return []

    return [data]
    result = []
    outlier = MathOutlierDetectorByMedian(getDeltaValue(data, "t"), 30)
    if len(outlier) > 0:
        prev = 0
        for i in outlier+[len(data)]:
            seg = data[prev:i]
            if len(seg) < 3:
                prev = i
                print "too short segment: " + str(prev) + ":" + str(i)
                continue
            result.append(seg)
            prev = i
        print "segments: " + str(len(result))
    else:
        result.append(data)

    return result

def prepareData(data):
    # set relative values
    MathRelativeValue(data)
    
    # detect too short movements
    shortRatio = shortMovementDetector(data, 15)
    print "short movement ratio: " + str(shortRatio)

    # compensate the points
    # data = MathCompensatePoint(data)

    # mirror for "Y" dim
    for i in data:
        i["y"] = -i["y"]

    return data, {"shortRatio": shortRatio}

def drawOne(content, dataHandler, paintHandler, paintPara="", signal=None, showFrequency=None, objFreq=None, meta=None):
    data = dataHandler(content)

    x = []
    y = []
    ix = 0
    iy = 0
    for entry in data:
        # print entry
        
        ix, iy, namex, namey = paintHandler(ix, iy, entry, paintPara)
        x.append(ix)
        y.append(iy)

    varietyRadio = MathVarietyRatio(y)
    outlier = MathOutlierDetectorByMedian(getDeltaValue(data, "t"), 30)
    print "outlier: " + str(outlier)
    print "varietyRadio: " + str(varietyRadio)

    fp = None
    if showFrequency:
        fp = objFreq.calculate([i[paintPara] for i in data])
        fpMaxI, fpMaxE = fp.maximum()
        meta["fpMaxIdx"] = fpMaxI

    p = signal.calculate({
        "pixel.x": x,
        "pixel.y": y,
        "title": dataHandler.func_name,
        "x_axis_label": namex,
        "y_axis_label": namey,
        "outlier": outlier,
    })

    meta["varietyRadio"] = varietyRadio
    obj = {
        "frequency": fp,
        "signal": p,
        "meta": meta
    }

    return obj

def drawRow(content, config, signal, freq, meta):
    row = []
    for cfg in config:
        dataHandler = cfg[0]
        paintHandler = cfg[1]
        paintPara = cfg[2]
        showFrequency = cfg[3] if len(cfg)>=4 else None

        row.append(drawOne(content, dataHandler, paintHandler, paintPara, signal, showFrequency, freq, meta))
    return row

class classAggregation:
    def __init__(self):
        self.data = []

    def calculate(self, index, entry):
        if len(self.data) <= index:
            self.data.append({"pixel.x": copy.deepcopy(entry.get("pixel.x")),
                            "pixel.y": copy.deepcopy(entry.get("pixel.y")),
                            "x_axis_label": entry.get("x_axis_label"),
                            "y_axis_label": entry.get("y_axis_label"),
                            "title": entry.get("title"),
                            })
        else:
            self.data[index]["pixel.x"] += entry.get("pixel.x")
            self.data[index]["pixel.y"] += entry.get("pixel.y")

    def draw(self):
        result = []
        for entry in self.data:
            p = figure(title=entry["title"], x_axis_label=entry["x_axis_label"], y_axis_label=entry["y_axis_label"])
            # p.line(entry["pixel.x"], entry["pixel.y"], line_width=2)
            p.circle(entry["pixel.x"], entry["pixel.y"], size=8)
            result += [p]
        return Row(children=result)

class classVarCollection:
    def __init__(self):
        self.data = []

    def calculate(self, index, entry):
        if len(self.data) <= index:
            allfields = {}
            for field in entry:
                allfields[field] = [entry.get(field)]
            self.data.append(allfields)
        else:
            for field in entry:
                self.data[index][field] += [entry.get(field)]

    def draw(self):
        result = []
        threshold = {"varietyRadio": 0.77, "shortRatio": 1, "fpMaxIdx": 2}
        for entry in self.data:
            column = []
            for field in entry:
                p = figure()
                p.circle(range(len(entry[field])), entry[field], size=4, color="blue")
                p.line(range(len(entry[field])), entry[field], line_width=2, legend=field)
                p.line([0,len(entry[field])], threshold[field], legend=str(threshold[field]), color="red", line_dash="dashed")
                column += [p]
            result += [Column(children=column)]
        return Row(children=result)

class classMinMax:
    def __init__(self, keys, count):
        self.data = {}
        for k in keys:
            self.data[k] = [[None,None] for i in range(count)]

    def minmax(self, rec, new):
        #min
        rec[0] = new[0] if not rec[0] else new[0] if new[0] < rec[0] else rec[0]
        #max
        rec[1] = new[1] if not rec[1] else new[1] if new[1] > rec[1] else rec[1]

    def calculate(self, entry, keys, index):
        for k in keys:
            e = entry[k]
            if len(e) > 0:
                self.minmax(self.data[k][index], [min(e),max(e)])

    def get(self, key, index):
        return self.data[key][index]

class classSignalChart(object):
    def __init__(self, objMinMax):
        self.objMinMax = objMinMax

    def calculate(self, data):
        new = self.__class__(self.objMinMax)
        new.data = data

        return new

    def minmax(self, index):
        self.objMinMax.calculate(self.data, ["pixel.x", "pixel.y"], index)

    def get(self, key):
        return self.data[key]

    def maximum(self):
        maxe = None
        maxi = None
        for i in range(len(self.data["pixel.x"])):
            if maxe==None or self.data["pixel.y"][i] > maxe:
                maxe = self.data["pixel.y"][i]
                maxi = i
        return maxi, maxe

    def tag(self, target, string):
        target.line([],[], legend=string)

    def draw(self, index, meta):
        x_axis_label=self.data["x_axis_label"]
        y_axis_label=self.data["y_axis_label"]
        x_range = self.objMinMax.get("pixel.x", index)
        y_range = self.objMinMax.get("pixel.y", index)

        if x_axis_label == "x" and y_axis_label == "y":
            # for XYPoint show
            mm = classMinMax([],0)
            mm.minmax(x_range, y_range)
            y_range = x_range

        p = figure(title=self.data["title"],
            x_axis_label=x_axis_label, y_axis_label=y_axis_label, x_range=x_range,y_range=y_range
            )
        p.line(self.data["pixel.x"], self.data["pixel.y"], line_width=2)
        p.circle(self.data["pixel.x"], self.data["pixel.y"], size=8)

        outlier = self.data["outlier"]
        p.circle([self.data["pixel.x"][i] for i in outlier], [self.data["pixel.y"][i] for i in outlier], size=16, color="red")

        self.tag(p, "varietyRadio: "+str(meta["varietyRadio"]))
        if meta != None:
            self.tag(p, "shortRatio: "+str(meta["shortRatio"]))

        return p

class classFrequencyChart(classSignalChart):
    def __init__(self, objMinMax):
        super(classFrequencyChart, self).__init__(objMinMax)

    def calculate(self, data):
        new = super(classFrequencyChart, self).calculate(data)

        freqs, spectrum = fft(data, len(data), use_db=False)
        new.data = {"pixel.x": freqs, "pixel.y": spectrum}

        return new

    def draw(self, index, meta):
        p = figure(width=800, height=300, title="FFT",
            x_axis_label="Frequency(Hz)", y_axis_label="Amplitude",
            x_range=self.objMinMax.get("pixel.x", index), y_range=self.objMinMax.get("pixel.y", index)
            )
        # p.line(self.data["pixel.x"], self.data["pixel.y"], legend="data", line_width=2, color="blue")
        tmp = getDeltaValue([ {"x": i}for i in self.data["pixel.x"]], "x")
        p.vbar(x=self.data["pixel.x"], top=self.data["pixel.y"], color="blue", width=min(tmp))#width=0.0002)

        return p

def drawChart(lines, begin, count, config):
    column = []
    cur = 0
    freq = classFrequencyChart(classMinMax(["pixel.x", "pixel.y"], len(config)))
    signal = classSignalChart(classMinMax(["pixel.x", "pixel.y"], len(config)))
    aggr = classAggregation()
    varCollection = classVarCollection()

    for content in lines:
        if cur < begin:
            cur += 1
            continue
        if cur >= begin+count:
            break
        cur += 1

        data = json.loads(content)

        segments = splitData(data)
        for data in segments:
            print "---------------------"
            data, meta = prepareData(data)
            if meta["shortRatio"] < 1.0:
                print "skip short movements: "+str(meta["shortRatio"])
                continue
            
            row = drawRow(data, config, signal, freq, meta)
            for i in range(len(row)):
                row[i]["signal"].minmax(i)

                if row[i]["frequency"]:
                    row[i]["frequency"].minmax(i)

            column.append(row)

    figureColumn = []
    for col in range(len(column)):
        figureRow = []
        for row in range(len(column[col])):
            entry = column[col][row]

            p = entry["signal"].draw(row, entry["meta"])
            p = p if not entry["frequency"] else Column(children=[p,entry["frequency"].draw(row, entry["meta"])])

            figureRow.append(p)

            aggr.calculate(row, entry["signal"])
            varCollection.calculate(row, entry["meta"])

        figureColumn.append(Row(children=figureRow))

    figureColumn.append(aggr.draw())
    figureColumn.append(varCollection.draw())

    chart = Column(children=figureColumn)
    output_file(sys.argv[1]+".html")
    show(chart)

config = [
##### first level
    [getPointRecords, drawXYPoint, "+"],
    [getPointRecords, drawWaveAt, "t"],

##### second level
    # [getVelocityRecords, drawORPoint, ""],
    # [getVelocityRecords, drawWaveAt, "theta", True],
    [getVelocityRecords, drawWaveAt, "distance", True],

##### third level
    # [getVelocityRateRecords, drawWaveAt, "theta", True],
    # [getVelocityRateRecords, drawWaveAt, "distance", True],

    # [getAccelerationRecords, drawORPoint, ""],
    # [getAccelerationRecords, drawWaveAt, "theta", True],
    # [getAccelerationRecords, drawWaveAt, "distance", True],

##### another method for speed/accelerate
    # [calculateAcceleration, drawORPoint, ""],
    # [calculateAcceleration, drawWaveDt, "theta", True],
    # [calculateAcceleration, drawWaveDt, "distance", True],
    # [calculateAcceleration, drawWaveDt, "t"],
]

drawChart(lines, 0, 100, config)

####### data analysis #######

import numpy as np
import matplotlib.pyplot as plt
import random
import scipy

COLOR_PALETTE = None
y_with_outlier = None

def test_init():
    global y_with_outlier, COLOR_PALETTE, y
    
    COLOR_PALETTE = [    
               "#348ABD",
               "#A60628",
               "#7A68A6",
               "#467821",
               "#CF4457",
               "#188487",
               "#E24A33"
              ]
    a = 1
    x = np.arange(1,50,.5)
    y = np.sin(-1/x) * np.sin(x)

    y_with_outlier = np.copy(y)

    # for ii in np.arange(len(x)/10, len(x), len(x)/10.):
    for ii in np.arange(len(x)/10, len(x), len(x)/10):
        y_with_outlier[ii]= 4*(random.random()-.5) + y[ii]

def get_median_filtered(signal, threshold = 3):
    """
    signal: is numpy array-like
    returns: signal, numpy array 
    """
    difference = np.abs(signal - np.median(signal))
    median_difference = np.median(difference)
    s = 0 if median_difference == 0 else difference / float(median_difference)
    mask = s > threshold
    signal[mask] = np.median(signal)
    return signal

def test_median_filtering():
    global y_with_outlier, COLOR_PALETTE, y

    plt.figure(figsize=(12, 6))
    window_size = 20
    outlier_s = y_with_outlier.tolist()
    median_filtered_signal = []

    for ii in range(0, y_with_outlier.size, window_size):
        median_filtered_signal += get_median_filtered(np.asanyarray(outlier_s[ii: ii+20])).tolist() 

    plt.subplot(2,1,1);
    plt.scatter(range(len(median_filtered_signal)), median_filtered_signal, c=COLOR_PALETTE[-1])
    plt.ylim([-1.5, 1.5])
    plt.xlim([0, 100])
    plt.title('Median Filtered Signal')
    plt.subplot(2,1,2);
    plt.scatter(range(len(y)), y, c=COLOR_PALETTE[-1])
    plt.ylim([-1, 1])
    plt.xlim([0, 100])
    plt.title('Original Signal')

    plt.show()

def detect_outlier_position_by_fft(signal, threshold_freq=.1, frequency_amplitude=.01):
    fft_of_signal = np.fft.fft(signal)
    outlier = np.max(signal) if abs(np.max(signal)) > abs(np.min(signal)) else np.min(signal)
    # if np.any(np.abs(fft_of_signal[threshold_freq:]) > frequency_amplitude):
    if np.any(np.abs(np.compress(np.greater_equal(fft_of_signal, threshold_freq), fft_of_signal)) > frequency_amplitude):
        index_of_outlier = np.where(signal == outlier)
        return index_of_outlier[0]
    else:
        return None

def test_fft_filtering():
    global y_with_outlier, COLOR_PALETTE
    
    outlier_positions = []
    for ii in range(10, y_with_outlier.size, 5):
        outlier_position = detect_outlier_position_by_fft(y_with_outlier[ii-5:ii+5])
        if outlier_position is not None:
            outlier_positions.append(ii + outlier_position[0] - 5)
    outlier_positions = list(set(outlier_positions))
    print outlier_positions

    plt.figure(figsize=(12, 6));
    plt.scatter(range(y_with_outlier.size), y_with_outlier, c=COLOR_PALETTE[0], label='Original Signal');
    plt.scatter(outlier_positions, y_with_outlier[np.asanyarray(outlier_positions)], c=COLOR_PALETTE[-1], label='Outliers');
    plt.legend();
    plt.show()

# test_init()
# test_median_filtering()
# test_fft_filtering()