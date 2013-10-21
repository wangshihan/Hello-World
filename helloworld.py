import globalConfig
import solvedCrashConfig
import SendMail
import os
import csv
import sys
import codecs
import shutil
import SendMail
import datetime
import globalConfig
import uuid
import utils

#dic的key排序
#实现起来有点丑，但是功能是OK的：）
def getSortedDictKeys(srcDict):
    tempKeyList = []
    for key in srcDict.keys():
        tempKeyList.append(key)
    tempKeyList.sort()

    resultKeyList = []
    nLen = len(tempKeyList) -1
    while  nLen>=0:
        resultKeyList.append(tempKeyList[nLen])
        nLen -= 1
    return  resultKeyList

#去掉最后的换行符
def removeEnter(input):
    result = input
    if result[-1] == '\n':
        result = result[0:-1]
    return result

#是否是己知的问题，主要是过滤掉已知的问题，方便查看新问题
def isKnownException(crashItem):
    if crashItem.brand in globalConfig.g_knownExceptionDic:
        knownExceptionList = globalConfig.g_knownExceptionDic[crashItem.brand]
        for e in knownExceptionList:
            if str(crashItem.stackTrace).find(e) != -1:
                return True

    #从全局的exception list中再捞一下
    for e in globalConfig.g_knowExceptionListWithNoBand:
        if str(crashItem.stackTrace).find(e) != -1:
            return True
    return False

#是否是已经解决的问题
def isSolvedException(crashItem):
    if not crashItem.appVersion in solvedCrashConfig.g_solvedCrashVersionDic:
        return False

    solvedCrashList = solvedCrashConfig.g_solvedCrashVersionDic[crashItem.appVersion]
    for solved in solvedCrashList:
        if str(crashItem.stackTrace).find(solved) != -1:
            return True
    return False

#读取UV
def readAndroidLoginUV_Old(fullCSVFileName):
    dir,name=os.path.split(fullCSVFileName)
    nameWithoutExt,ext=os.path.splitext(name)
    resultFileName = dir  + "\\"+nameWithoutExt + ".txt"
    androidUVDic = dict()
    if os.path.exists(resultFileName) != True:
        return androidUVDic

    global g_UVFile
    g_UVFile = resultFileName
    fp = open(resultFileName, "r")
    hasAndroid = False
    verName = ""
    for line in fp:
        #查找含有android关键字的行
        if hasAndroid:
            androidUVDic[verName] = int(removeEnter(line))
            hasAndroid = False
        else:
            if line.find("ANDROID") != -1:
                hasAndroid = True
                verName = removeEnter(line)
            else:
                hasAndroid = False
    return androidUVDic

#读取UV
def readAndroidLoginUV(fullCSVFileName):
    dir,name=os.path.split(fullCSVFileName)
    nameWithoutExt,ext=os.path.splitext(name)
    resultFileName = dir  + "\\"+nameWithoutExt + ".txt"
    androidUVDic = dict()
    if not os.path.exists(resultFileName):
        return androidUVDic

    global g_UVFile
    g_UVFile = resultFileName
    fp = open(resultFileName, "r")

    for line in fp:
        myList = line.split(" ")
        versionName = myList[0]
        if line.find("ANDROID") != -1:
            androidUVDic[versionName] = int(myList[len(myList)-1])
    return androidUVDic

#读取新的UV
def readNewAndroidLoginUI(fullCSVFileName):
    f = open(fullCSVFileName,openMode)
     #存成字典
    csvContent  = csv.DictReader(f)
    androidUVDic = dict()
    for dictRow in csvContent:
        versionName = dictRow["logon_client_version"]
        if versionName.find("ANDROID") != -1:
            androidUVDic[versionName] = int(myList[len(myList)-1])

    return androidUVDic

#获取指定目前下的所有csv文件
def getCSVFile():
    for root,dirs,files in os.walk(globalConfig.g_srcFileRootDir):
        allCsvFils = []
        for allfiles in files:
            fullFileName = root
            fullFileName += allfiles
            f,ext=os.path.splitext(fullFileName)
            ext.lower()
            if ext == ".csv":
                allCsvFils.append(fullFileName)
    return allCsvFils

#存放各种版本的crash
class CSummary:
    def __init__(self):
        self.totalCount = 0
        #key:版本,value: CVersionCrash
        self.dic = dict()

#存放同一版本，不同crash类型
class CVersionCrash:
    def __init__(self):
        self.version = "unknown"
        self.dic = dict()#key:异常描述,value: CrashItem
        self.totalCount = 0
        self.knownCrashCount = 0
        self.fixedCrashCount = 0#已解决的crash
    def addItem(self,crashItem):
        self.totalCount += 1
        if crashItem.exception in self.dic:
            self.dic[crashItem.exception].append(crashItem)
        else:
            tempList = []
            tempList.append(crashItem)
            self.dic[crashItem.exception] = tempList

    #根据crash数目从高到低排序
    def getSortedCrash(self):
        resultList = []
        for exceptionKey in self.dic:
            crashCount = len(self.dic[exceptionKey])
            index = 0
            insertOK = False
            for myKey in resultList:
                tempLen = len(self.dic[myKey])
                if crashCount >= tempLen:
                    resultList.insert(index, exceptionKey)
                    insertOK = True
                    break;
                else:
                    index += 1
            if not insertOK:
                resultList.append(exceptionKey)
        return resultList

class CrashItem:
    def __init__(self):
        self.appVersion = "unknown"    #版本号
        self.userNick = "unknown"       #用户ID号
        self.exception = "unknown"      #异常类型
        self.stackTrace = "unknown"     #异常堆栈
        self.brand = "unknown"
        self.os_version = "unknown"
        self.access  = "unknown"
        self.deviceID = "unknown"
        self.local_time = "unknown"
        self.unique = ""                 #标识唯一一条记录，主要用于产生文件名
        self.crashStackTraceURL ="unknown"    #堆栈信息地址（URL）

#将stack trace写成文件，方便阅读
def parseAndSaveStackTrace(crashItem):
    #将堆栈与操作记分开
    try:
        stackAndOperation = crashItem.stackTrace.split("OperatorHistory=====>")
        if len(stackAndOperation) != 2:
            print("")
        else:
            #解析stackTrace
            stackTrace = stackAndOperation[0].split("++")
            shortFileName = crashItem.unique + ".txt"

            fullFileName = globalConfig.g_crashFileRootDir + shortFileName
            file_object = codecs.open(fullFileName, "w", "utf-8")
            #file_object = open(fullFileName, 'w')
            #写入一些用户信息
            file_object.write("userID:" + crashItem.userNick + "\r\n")
            file_object.write("brand:" + crashItem.brand + "\r\n")
            file_object.write("access:" + crashItem.access + "\r\n")
            file_object.write("localtime:" + crashItem.local_time + "\r\n")
            file_object.write("deviceID:" + crashItem.deviceID + "\r\n");
            file_object.write("osversion:" + crashItem.os_version + "\r\n\r\n")

            for line in stackTrace:
                file_object.write(line)
                file_object.write("\r\n")

            #解析操作记录
            operateTrace = stackAndOperation[1].split(",")
            file_object.write("\r\n\r\nOperatorHistory=====>\r\n")
            for line in operateTrace:
                file_object.write(line)
                file_object.write("\r\n")

            file_object.close();
            #保存URL地址
            crashItem.crashStackTraceURL = globalConfig.g_httpUrl + shortFileName
            g_crashItemList.append(crashItem)
    except:
        print("")

#清空历史数据
utils.cleanOldDirs(utils.getCrashLogDir())

g_androidUV = dict()
allCsvFiles = getCSVFile()

openMode = "r"

#保存当前的UV文件
g_UVFile = ""

for csvFilePath in allCsvFiles:
    #开始读取FTP上的UV文件
    tempCSVNameList = csvFilePath.split("\\")
    UVFileNameAtFtp = tempCSVNameList[len(tempCSVNameList)-1]
    #CSV文件与FTP的文件是有一定规定的对应
    UVFileNameAtFtp = "logon.statics." + UVFileNameAtFtp.replace(".csv", "")

    #FTP下载后要保存的UV文件名
    UVFileToSave = globalConfig.g_srcFileRootDir + UVFileNameAtFtp.replace("logon.statics.","")
    UVFileToSave += ".txt"
    #文件名就绪，开始FTP获取
    utils.fetchUVDataFromFTP(globalConfig.g_srcFileRootDir  + UVFileNameAtFtp, UVFileToSave)

    #读UV文件
    g_androidUV = readAndroidLoginUV(csvFilePath)

    #g_androidUV = readAndroidLoginUV_Old(csvFilePath)
    #没有UV文件，不再继续
    if len(g_androidUV) <= 0:
        continue

    #读取CSV
    csvFilePath = utils.getCsvCorrectFilePath(csvFilePath)
    if  not os.path.exists(csvFilePath):
        continue

    f = open(csvFilePath,openMode)
    #存成字典
    csvContent = csv.DictReader(f)

    g_crashItemList = []

    for dictRow in csvContent:
        item = CrashItem()
        #字典所用的字段要与csv一致

        #ver的一些特殊处理，如果没有_ANDROID_WW，需要加上
        item.appVersion = utils.addEndVersionFlag(dictRow['app_version'])
        item.userNick = dictRow['user_nick']
        #item.unique = dictRow['arg1']
        item.unique = str(uuid.uuid1())
        item.exception = dictRow['arg2']
        item.stackTrace = dictRow['args']
        item.deviceID = dictRow['device_id']
        item.access = dictRow['access']
        item.os_version = dictRow['os_version']
        item.brand = dictRow['brand']
        item.local_time = dictRow['local_time']
        parseAndSaveStackTrace(item)

    summary = CSummary()
    summary.totalCount = len(g_crashItemList)#crash 总的目数

    for crashItem in g_crashItemList:
        if crashItem.appVersion in summary.dic:
            versionCrash = summary.dic[crashItem.appVersion]
            versionCrash.addItem(crashItem)
        else:
            versionCrash = CVersionCrash()
            versionCrash.appVersion = crashItem.appVersion
            versionCrash.addItem(crashItem)
            summary.dic[crashItem.appVersion] = versionCrash

        #统计己知的问题
        if isKnownException(crashItem):
            versionCrash = summary.dic[crashItem.appVersion]
            versionCrash.knownCrashCount += 1

        #统计已经fixed的问题
        if isSolvedException(crashItem):
            versionCrash = summary.dic[crashItem.appVersion]
            versionCrash.fixedCrashCount += 1

    strEmailContent = ""
    strEmailContent = "Crash 数量：%d 次" %(summary.totalCount)
    strEmailContent += "\r\n\r\n"
    strEmailContent += "各版本情况如下：\r\n"

    keyList = getSortedDictKeys(summary.dic)
    for key in keyList:
    #for key in summary.dic.keys():
        versionCrash = summary.dic[key]
        #if g_androidUV.has_key(versionCrash.appVersion):
        try:
            uv = g_androidUV[versionCrash.appVersion]
            crashPercent = (versionCrash.totalCount*1.0/uv)*100
            crashPercent = round(crashPercent,3)
            crashPercent = str(crashPercent)+"%"

            if uv-versionCrash.knownCrashCount == 0:
                crashPercent2 = "0.00%"
            else:
                crashPercent2 = ((versionCrash.totalCount-versionCrash.knownCrashCount)*1.0/uv)*100
                crashPercent2 = round(crashPercent2,3)
                crashPercent2 = str(crashPercent2)+"%"

             #计算排除已经解决的crash
            if uv - versionCrash.fixedCrashCount == 0:
                crashPercentExcludeFixed = "0.00%"
            else:
                crashPercentExcludeFixed = ((versionCrash.totalCount-versionCrash.fixedCrashCount)*1.0/uv)*100
                crashPercentExcludeFixed = round(crashPercentExcludeFixed,3)
                crashPercentExcludeFixed = str(crashPercentExcludeFixed)+"%"
            uv = str(uv)
        except:
            crashPercent = "未知"
            crashPercent2 = "未知"
            uv = "未知"
            uv2 ="未知"

        strFormatVersion = str(versionCrash.appVersion).ljust(20)
        strEmailContent += "%s %s次 UV：%s \t\t crash比率：%s \tFixed: %s \t crash比率(ExcludeFixed)：%s \t KE:%s \t\tcrash比率(Exclude KE)：%s \r\n"  \
                           %(strFormatVersion, str(versionCrash.totalCount).rjust(10),\
                             uv,crashPercent,versionCrash.fixedCrashCount, crashPercentExcludeFixed,str(versionCrash.knownCrashCount),crashPercent2)

    strEmailContent += "\r\n\r\ncrash比率(ExcludeFixed)，排除掉已经解决的问题。计算方式：(crash-fixedCrashCount)/UV"
    strEmailContent += "\r\nKE:因系统定制造成的己知问题(KnownException)\r\n"
    strEmailContent += "计算方式：(crash-KE)/UV\r\n"
    strEmailContent += "\r\nKE:\r\n" + globalConfig.getKnownExceptionDescription()
    strSummary = ""

    keyList = getSortedDictKeys(summary.dic)
    for key in keyList:
        versionCrash = summary.dic[key]
        strSummary += "\r\n---版本：%s %d次 \r\n"  %(versionCrash.appVersion, versionCrash.totalCount)
        crashException = versionCrash.getSortedCrash()
        for exceptionKey in crashException:
            strSummary += "异常：%s %d次\r\n" %(exceptionKey, len(versionCrash.dic[exceptionKey]))
            strSummary += "相关LOG地址:\r\n"
            userCrashDic = dict()
            for crashItem in versionCrash.dic[exceptionKey]:
                #同一个版本同一种CRASH，再根据用户归类
                if crashItem.userNick in userCrashDic:
                    tempList = userCrashDic[crashItem.userNick]
                    #不是己知问题，并且也未解决的问题，加入
                    if not isKnownException(crashItem) and not isSolvedException(crashItem):
                        tempList.append(crashItem.crashStackTraceURL)
                else:
                    crashStackList = list()
                    #不是己知问题，并且也未解决的问题，加入
                    if not isKnownException(crashItem) and not isSolvedException(crashItem):
                        crashStackList.append(crashItem.crashStackTraceURL)
                    userCrashDic[crashItem.userNick] = crashStackList

            for key in userCrashDic.keys():
                tempList = userCrashDic[key]
                if len(tempList) > 0:
                    strSummary += "\t"+key + ":\r\n"
                    for url in tempList:
                        strSummary += "\t\t"+url+"\r\n"
                    strSummary += "\r\n"
            strSummary += "\r\n"

    strEmailContent += strSummary

    #复制CSV文件到http目录
    shutil.copy(csvFilePath, globalConfig.g_crashFileRootDir)
    p,fname=os.path.split(csvFilePath);
    csvMailContent = "csv文件："+ globalConfig.g_httpUrl + fname
    strEmailContent = csvMailContent + "\r\n" + strEmailContent

    #发邮件
    subject = os.path.splitext(fname)
    SendMail.SendSimplEmail(strEmailContent, subject[0])

   # print(strEmailContent)
    #做清理工作
    f.close()
    os.remove(csvFilePath)
    os.remove(g_UVFile)
