#!/usr/bin/env python
import sys
from sklearn import preprocessing
import json
import numpy as np

from sklearn.cross_validation import train_test_split
import pandas as pd
####### config #######
from sklearn.cluster import SpectralClustering
from sklearn.cluster import Birch

features = ["captcha_browserPower",
            "captcha_freqMaxIdx",
            # "captcha_guid",
            "captcha_recordCount",
            "captcha_segmentCount",
            "captcha_shortRatio",
            "captcha_varietyRatio",
            "captcha_verify_id",
            "id",
            "clickCount",
            "duration",
            "os",
            "browser",
            "status",
            "path"]
scaler = preprocessing.StandardScaler()

####### customer training #######

from sklearn import metrics
def evaluateScore(X, y_pred=None, model=None):
    score = metrics.calinski_harabaz_score(X, y_pred)
    # print "Calinski-Harabasz Score", score
    return score

def doMachineLearning(X, Y=None):
    scores = {"min": 1000000, "max": 0}
    result = None
    paras = None
    for c in (2,3,4,5,6,7,8,9):
        for b in (20,30,40,50,60,70):
            for t in (0.3,0.4,0.5,0.6):
                model = Birch(n_clusters = c, branching_factor=b, threshold=t)
                model.set_params()
                y_pred = model.fit_predict(X)
                # print "result: ", y_pred

                #evaluate score for result
                score = evaluateScore(X, y_pred)
                result = y_pred if score > scores["max"] else result
                paras = "cluster={0}, branch={1}, threshold={2}".format(c,b,t) if score > scores["max"] else paras
                scores["max"] = score if score > scores["max"] else scores["max"]
                scores["min"] = score if score < scores["min"] else scores["min"]

    print "select paras: ", paras
    return result, scores["max"]

# def doMachineLearning(X, Y=None):
#     model = SpectralClustering()
#     y_pred = model.fit_predict(X)
#     score = evaluateScore(X, y_pred)
#     return y_pred, score

####### common API #######
def readFile():
    if len(sys.argv) != 2:
        print "Usage: {0} <filename>".format(sys.argv[0])
        sys.exit()

    filename = sys.argv[1]
    file = open(filename, 'r')
    lines = file.readlines()
        
    print "total ", len(lines), " records"
    return lines

def parseData(lines):
    result = []
    for line in lines:
        data = json.loads(line)
        #get wanted data into result
        # result += [data]
        if data.get("result"):
            result += [data["result"]]

    return result

def _isNumeric(data):
    return type(data)==int or type(data)==float

def _tryToNumeric(data):
    try:
        return float(data)
    except Exception as e:
        return None

def numericFeatures(data, features, filled=None):
    featureMap = {}
    for f in features:
        convertDirect = False
        hasValue = False
        for d in data:
            v = d.get(f)
            if _isNumeric(v):
                hasValue = True
                break
            if v == None:
                if _isNumeric(filled):
                    d[f] = filled   #fill empty field with value
                continue
            
            #now need to convert
            hasValue = True

            #firstly try to convert directly
            tmp = _tryToNumeric(v)
            if _isNumeric(tmp):
                d[f] = tmp
                convertDirect = True
                continue

            if convertDirect:
                print "Field \"{0}\" has been converted directly before but now can't convert directly! Pls check all the value of this field".format(f)
                sys.exit()

            #otherwise convert from map
            m = {"count": 0, "map": {}} if not featureMap.get(f) else featureMap.get(f)
            if m["map"].get(v) != None:
                d[f] = m["count"]   #override original data
                continue
            
            #add new enum
            m["map"][v] = m["count"]
            d[f] = m["count"]   #override original data
            m["count"] += 1

            featureMap[f] = m

        if not hasValue:
            print "Field \"{0}\" has no any value found!".format(f)
            sys.exit()

    return featureMap

from sklearn.preprocessing import OneHotEncoder
def extractTrainingData(data, features, fmap=None):
    result = []
    for d in data:
        e = []
        for f in features:
            e += [d[f]]
        result += [e]

    result = np.array(result)

    #encoding if necessary
    if fmap:
        needToEncode = None
        remainder = None
        #split which features need to be encoded
        for i in range(len(features)):
            e = result[:,i:i+1]
            if features[i] in fmap.keys():
                if type(needToEncode) != type(None):
                    needToEncode = np.concatenate((needToEncode, e), axis=1)
                else:
                    needToEncode = e
            else:
                if type(remainder) != type(None):
                    remainder = np.concatenate((remainder, e), axis=1)
                else:
                    remainder = e
            
        #do encoding
        enc = OneHotEncoder()
        enc.fit(needToEncode)
        needToEncode = enc.transform(needToEncode).toarray()

        #merge back
        result = np.concatenate((remainder, needToEncode), axis=1)

    return result

def saveResult(rawData, y_pred):
    fn = sys.argv[1]
    categories = list(set(np.asarray(y_pred)))
    categories.sort()
    filenames = [fn+"~"+str(i) for i in categories]
    files = [open(fn, 'w') for fn in filenames]
    for i in range(len(rawData)):
        if i >= len(y_pred):
            break

        jsonData = rawData[i]
        jsonData = json.loads(jsonData)
        jsonData = jsonData.get("result")
        jsonData = json.dumps(jsonData) + "\n"
        files[y_pred[i]].writelines([jsonData])

    for f in files:
        f.close()

    print "save result into files: ", filenames

####### entry point #######

def main():
    #read data from file
    rawData = readFile()

    #convert data to json
    data = parseData(rawData)

    #select features
    global features
    print "select features: ", features

    #convert some non-numeric features to numeric
    fmap = numericFeatures(data, features, filled=-1)
    print "feature map: ", fmap

    #prepare training data
    X = extractTrainingData(data, features, fmap)

    #preprocess data
    global scaler
    scaler.fit(X)
    X_ = scaler.transform(X)

    #split data into training and validation

    #do machine learning
    y_pred, score = doMachineLearning(X_)
    print "score={0}, list={1}".format(score, y_pred)

    #output result if necessary
    saveResult(rawData, y_pred)

####### begin #######
main()
