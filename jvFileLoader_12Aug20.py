#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 15:49:36 2020

@author: rbramant
"""

from numpy import loadtxt
import pandas as pd
import numpy as np
import scipy.interpolate as interpolate
from scipy.stats import linregress
from csv import writer
import mmap
import re
import SortAndPlotFunctions_12Aug20 as spf


class LoadData:
    # df = pd.DataFrame()
    # badFormatLoadList = []
    # noisyCurveLoadList = []
    def __init__(self):
        # self.df = pd.DataFrame()
        self.badFormatLoadList = []
        self.noisyCurveLoadList = []
        self.df = pd.DataFrame()
        self.dfP = pd.DataFrame()
        self.dfnumpy = pd.DataFrame()
    def loadDataFromFileManager(self, fileNames, solarSim="SERFC215 racetrack sim", module=False):
        # LoadData.df = LoadData.df[0:0]
        self.fileNames = fileNames
        self.solarSim = solarSim
        self.module = module
        if solarSim == "SERFC215 racetrack sim":
            self.racetrack = True
        else:
            self.racetrack = False
        
        for f in fileNames:
            newDevice = PvDevice(f, self.solarSim, self.module, self.racetrack)
            newDevice.deviceDataFromLoad_set(f,self.solarSim)
            newDevice.deviceDataFromCalc_set()
            # dfTemp = newDevice.dataFrameDict_get()
            badFormat = newDevice.badFormat_get()
            noisyCurve = newDevice.noisyCurve_get()
            # dataNP, dataDict, badFormatTemp = loadDataFromSolarSim(f, solarSim) # do we need an if else for reload DF?
            # split0 = f.split('/') ### splitting off path from filename
            # dfTemp, noisyCurveTemp = jvAnalysis(split0[-1], dataNP, dataDict, module)
            if len(badFormat)>0:
                self.badFormatLoadList.append(badFormat)
            else:
                self.badFormatLoadList = ''
            self.noisyCurveLoadList.append(noisyCurve)
            # self.df = pd.concat([self.df,dfTemp])
            # LoadData.df = pd.concat([LoadData.df, dfTemp])
            # LoadData.badFormatLoadList.append(badFormatTemp)
            # LoadData.noisyCurveLoadList.append(noisyCurveTemp)
        # calculate Hysteresis:
        
        with open('badFormat.csv', 'w') as f: # creating and opening a .csv file
            bad = writer(f, delimiter=',') #setting delimiter as a ,
            #writer.writerows([header]) #write header
            bad.writerows(zip(self.badFormatLoadList)) # write data
        # return loadData.df, loadData.badFormatList, loadData.noisyCurveList
        # PvDevice.findHystGroups_set(self)
        self.df = PvDevice.devicesDF_get(self)
        hysteresis = spf.ScanDirections(self.df.copy())
        print(hysteresis.dfNorm)
        hysteresis.calcHysteresis()
        self.df = hysteresis.dfHyst.copy()
        print(self.df)
    def loadParametersFromFileManager(self, fileName, addDevice = False):
        try:
            if addDevice == False:
                self.paramsDf = pd.read_csv(fileName, header=[0,1], true_values=['TRUE'],
                                            false_values=['FALSE'])
                self.dfP = pd.concat([self.dfP,self.paramsDf])
            if addDevice == True:
                self.paramsDf = pd.read_csv(fileName, sep=',')
                self.df = pd.concat([self.df, self.paramsDf])
            
        except: 
            self.badFormatLoadList = fileName
    def loadDF_destroy(self):
        self.df = pd.DataFrame()
        self.dfP = pd.DataFrame()
        PvDevice.devicesDF_destroy(self)
        print('dataframes destroyed')
            
    
## edit everything below here to call class attributes!
## change the way we report files, so that it populates the text file at the end.
class PvDevice:
    #columns not applied. Would need to assign value to Module or Racetrack instead of
    # 'if 'Pixel' in DataFrame' in a lot of places.
    # columnsDevices = ['User Initials', 'Sample', 'Pixel', 'LightDark',
    #                   'Scan Direction', 'Scan', 'Cell Area', 'Number Cells',
    #                   'Voc', 'Voc per Cell', 'Voc Hyst', 'Vmpp', 'Vmpp Hyst',
    #                   'Jsc', 'Jsc Per Cell', 'Jsc Hyst', 'Jmpp', 'FF', 'FF Hyst',
    #                   'PCE', 'PCE Hyst', 'Rs', 'Rs Hyst', 'Rsh', 'Rsh Hyst',
    #                   'File', 'Folder', 'Path', 'Solar Simulator']
    __devicesDF = pd.DataFrame()
    def __init__(self, filename = '[no file selected]', solarSim='[no solar sim selected]',
                 module=False, racetrack=True):
        #variables selected using radio buttons or load file dialogue
        self.filename = filename
        self.solarSim = solarSim
        self.module = module
        self.racetrack = racetrack
        
        #variables below can usually be extracted from filename or JV data file:
        self.__badFormatTemp = '' #log badly formatted files
        self.__noisyCurveTemp = '' #log noisy curves
        self.__dataJV = [] # fill numpy array with data using methods
        self.__dataJVdf = pd.DataFrame()
        self.__dataDF = pd.DataFrame()
        self.user = '[no user initials]' # person made the sample
        self.sampleName = '[no sample name]'
        self.scanDir = '[no scan direction]'
        self.jvType = '[no light/dark condition specified]' # can be 'lt' or 'dk'
        self.pixNum = '[no pixel]' #can be 'pxA', 'pxB', ..., 'pxF'
        self.numCells = 1 #must be set to number of cells in a module
        self.cellArea = 0.06 #default area of racetrack pixel is 0.06cm^2
        self.loopNum = 0
        self.scanNum = 0
        
        # self.__deviceDict = {}
        self.voc = 0.0
        self.vocHyst = 0.0
        self.jsc = 0.0
        self.jscHyst = 0.0
        self.vmpp = 0.0
        self.vmppHyst = 0.0
        self.jmpp = 0.0
        self.jmppHyst = 0.0
        self.pce = 0.0
        self.pceHyst = 0.0
        self.ff = 0.0
        self.ffHyst = 0.0
        self.rs = 0.0
        self.rsHyst = 0.0
        self.rsh = 0.0
        self.rshHyst = 0.0
        
        #variables below must be assigned manually or using metadata loader:
        self.perovskite = '[no perovskite type]'
        self.holeTL = '[no hole transport layer]'
        self.elecTL = '[no electron transport layer]'
        self.topCon = '[no top contact]'
        self.botCon = '[no bottom contact]'
        self.devType = 'nip' #can be 'nip' or 'pin'
        self.timeStampJV = 0 #compatibility with degradation data
    
    def calcVoc(self):
        data = self.__dataJV[:]
        voltage = data[:,0]
        cd = data[:,1]
        f2 = interpolate.interp1d(cd, voltage, bounds_error=False,
                                      fill_value = "extrapolate")
        vocTemp = f2(0)
        vocTemp = float(vocTemp)
        self.voc = vocTemp
    def calcJsc(self):
        data = self.__dataJV[:]
        voltage = data[:,0]
        cd = data[:,1]
        f = interpolate.interp1d(voltage, cd, bounds_error=False,
                                     fill_value = "extrapolate")
        jscTemp = f(0) ### the jsc is the current at voltage  = 0
        jscTemp = float(jscTemp) ### converting to a float
        self.jsc = jscTemp
    def calcVmppJmpp(self):
        data = self.__dataJV[:]
        voltage = data[:,0]
        cd = data[:,1]
        f = interpolate.interp1d(voltage, cd, bounds_error=False,
                                     fill_value = "extrapolate")
        xnew = np.linspace(voltage[0], voltage[-1], num = 1000)  #### creating finer grid to find Voc, Vmpp, Jmpp (this may not be necesary)
        power = xnew*f(xnew) #power as a function of V
        if self.jsc < 0:
                power = power * -1
                self.jsc = abs(self.jsc)
        mppIndex = power.argmax() ### mmp = max power point, finding max power point
        vmppTemp = xnew[mppIndex] #V at mpp
        vmppTemp = np.around(vmppTemp,4)  ### rounding to a more reasonable number of sig figs
        self.vmpp = vmppTemp
        jmppTemp = f(xnew[mppIndex]) ## current at mmp
        jmppTemp = np.around(jmppTemp,4)
        self.jmpp = jmppTemp
        
    def calcFF(self):
        jmppTemp = self.jmpp
        vmppTemp = self.vmpp
        vocTemp = self.voc
        jscTemp = self.jsc
        ffTemp = (vmppTemp*jmppTemp)/(vocTemp*jscTemp)*100  ### calculating fill factor
        ffTemp = np.around(ffTemp,4)
        self.ff = ffTemp
    def calcPCE(self):
        jmppTemp = self.jmpp
        vmppTemp = self.vmpp
        effTemp = jmppTemp*vmppTemp  ### calculating efficiency 
        effTemp = np.around(effTemp,4)
        self.pce = effTemp
    def calcRs(self):
        #### calculating Rs
        ### this method is not very robust, if the curves are really bad it may not be accurate
        ###################################
        data = self.__dataJV[:]
        voltage = data[:,0]
        cd = data[:,1]
        vocTemp = self.voc
        vocInd = np.abs(voltage - vocTemp).argmin()  #### finding the index in the vector where Voc occurs
        vocX = np.zeros(3)     ### declaring array to put a portion of the IV curve for fitting
        vocY = np.zeros(3)
        vocX = voltage[vocInd-1:vocInd+1]   ### taking data points from IV curve and placing them in the array
        vocY = cd[vocInd-1:vocInd+1]
        try:
            vocLinFit = linregress(vocX, vocY)  ### fitting a line and getting the slope
            Rs = -1000/vocLinFit.slope   ### Rs = 1/slope. I think the units here are just ohms
        except:
            Rs = np.NaN
        #Rs = Rs/cellA
        self.rs = Rs
    def calcRsh(self):
        #### calculating Rsh
        ### this method is not very robust, if the curves are really bad it may not be accurate
           ###################################
        data = self.__dataJV[:]
        voltage = data[:,0]
        cd = data[:,1]
        jscTemp = self.jsc
        jscInd = np.abs(cd - jscTemp).argmin()## finding the index in the vector where jsc occurs
        jscX = np.zeros(40)    ### declaring array to put a portion of the IV curve for fitting
        jscY = np.zeros(40)  
        jscX = voltage[jscInd-19:jscInd+20]
        jscY = cd[jscInd-19:jscInd+20]
        try:
            jscLinFit = linregress(jscX, jscY)
            Rsh = -1000/jscLinFit.slope
        except:
            Rsh = np.NaN
        #Rsh = Rsh/cellA
        self.rsh = Rsh
    def deviceDataFromCalc_set(self):
        # print(self.__dataDF)
        self.jvType = self.__dataDF['LightDark'][0]
        if self.jvType == 'lt':
            PvDevice.calcVoc(self)
            PvDevice.calcJsc(self)
            PvDevice.calcVmppJmpp(self)
            PvDevice.calcFF(self)
            PvDevice.calcPCE(self)
            PvDevice.calcRs(self)
            PvDevice.calcRsh(self)
            self.__dataDF['Voc'] = self.voc
            self.__dataDF['Jsc'] = self.jsc
            self.__dataDF['FF'] = self.ff
            self.__dataDF['PCE'] = self.pce
            self.__dataDF['Vmpp'] = self.vmpp
            self.__dataDF['Jmpp'] = self.jmpp
            self.__dataDF['Rs'] = self.rs
            self.__dataDF['Rsh'] = self.rsh
            PvDevice.__devicesDF = pd.concat([PvDevice.__devicesDF, self.__dataDF])
            # print(PvDevice.__devicesDF)
            # return self.__dataDF.copy()
        elif self.jvType == 'dk':
            print('Dark Curve Operations Here')
        else:
            print("Light/Dark specification incorrectly formatted")
    def deviceDataFromLoad_set(self, filename, solarSim):
        self.filename = filename
        self.solarSim = solarSim
        badFormatTemp = '' # declaring the list to store
        dfLoadTemp = {}
        dataNPtemp=[]
        loader = SimLoader()
        try:
            if self.solarSim == "SERFC215 racetrack sim":
                loader.SERFC215rt(self.filename)
                dataNPtemp = loader.dataNP
                dfLoadTemp = loader.dataDF
                # dictLoadTemp = loader.dataDict
            elif self.solarSim == "PDIL substrate sim" & self.module == False:
                loader.STF213sub(self.filename)
                dataNPtemp = loader.dataNP
                dfLoadTemp = loader.dataDF
                # dictLoadTemp = loader.dataDict
            elif self.solarSim == "STF204 indoor light sim" & self.module == False:
                loader.STF204in(self.filename)
                dataNPtemp = loader.dataNP
                dfLoadTemp = loader.dataDF
                # dictLoadTemp = loader.dataDict
            elif self.solarSim == "STF136 superstrate sim" & self.module == False:
                loader.STF136sup(self.filename)
                dataNPtemp = loader.dataNP
                dfLoadTemp = loader.dataDF
                # dictLoadTemp = loader.dataDict
            elif self.solarSim == "reload DF":
                #load pickle to dfLoadTemp.
                print("This is a csv for loading parameters")
            else:
                print("Please choose a solar simulator")
    #        jvType = ['lt', 'dk'] need to find way to deal with dark vs light curves in same file
            # also need to find out how to load only one block of text without specifying the number of rows - true for all!
        except:
            print("Please double check solar simulator selection. "
                  + filename + " format is incompatible")
            badFormatTemp = filename
        ### writing a file which has the names of all the files which weren't formatted correctly
        self.__dataJV = dataNPtemp
        self.__dataDF = dfLoadTemp
        # self.__deviceDict = dictLoadTemp
        self.__badFormatTemp = badFormatTemp
        # return dataNPtemp, dfLoadTemp, badFormatTemp
    def devicesDF_get(self):
        dfReturn = PvDevice.__devicesDF.copy()
        return dfReturn
    def badFormat_get(self):
        return self.__badFormatTemp
    def noisyCurve_get(self):
        return self.__noisyCurveTemp
    def devicesDF_destroy(self):
        PvDevice.__devicesDF = pd.DataFrame()
  
def parametersLoader(filename, data):
    paramsDf = pd.read_csv(filename, sep=',')
    df = pd.merge(data,paramsDf,on='Sample',how='inner')
    return df


##### solar simulator specific loaders:
class SimLoader:
    ## only SERFC215rt has been tested to see if it works
    def __init__(self):
        self.filename = '[no filename specified]'
        self.dataNP = []
        self.dataDict = {}
        self.dataDF = pd.DataFrame()
        
    def SERFC215rt(self,filename):
        self.filename = filename
        self.dataNP = loadtxt(self.filename, delimiter='\t', skiprows=21, usecols=[0,1],
                       dtype=float) ### putting IV data into array
    
        try:
            split0 = self.filename.split('/') ### splitting off path from filename
            file = split0[-1]
            path = split0[0:-1]
            folder = split0[-2]
            split1 = split0[-1].split('.') ### splitting the string with . as a delimiter
            fileNameSplit = split1[0].split('_') #splitting again with _
            user = fileNameSplit[0]     # user initials is first col [0]
            sampleName = fileNameSplit[1]     # cell name is second col [1]
            scanDir = fileNameSplit[-5]    # scan direction is the third [2]
            jvType = fileNameSplit[-4]    # jvType is fourth [3]
            loopNum = fileNameSplit[-3]    # loop number is the fifth [4]
            pixNum = fileNameSplit[-2]   # pixel letter is 6th [5]
            scanNum = fileNameSplit[-1]  # scan number is 7th [6]
            self.dataDict = {'Path': path, 'Folder': folder, 'File': file, 'Solar Simulator': "SERFC215 racetrack sim",
              'User Initials': user, 'Sample': sampleName, 'Pixel': pixNum,
              'Loop': loopNum, 'Scan': scanNum, 'Scan Direction': scanDir,
              'LightDark': jvType}
            self.dataDF = self.dataDF.append(self.dataDict, ignore_index=True)
        except:
            print("File naming convention incompatible for" + self.filename +
                  ". Format should be " +
                  "<user>_<sampleName>_<rev/fwd>_<lt/dk>_lp<#>_<pixel>_<scan number>")
        # return self.dataNP, self.dataDict
    
    
    def STF213sub(self,filename):
        self.filename = filename
        self.dataNP = loadtxt(self.filename, skiprows=2, nrows=120, delimiter='\t',
                               usecols=[0,1], dtype=float) ###putting IV data into array
        try:
            split0 = self.filename.split('/') ### splitting off path from filename
            file = split0[-1]
            path = split0[0:-1]
            folder = split0[-2]
            split1 = split0[-1].split('.') ### splitting the string with . as a delimiter
            fileNameSplit = split1[0].split('_') #splitting again with _
            user = fileNameSplit[0]     # user initials is first col [0]
            sampleName = fileNameSplit[1]     # cell name is second col [1]
            scanDir = fileNameSplit[2]    # scan direction is the third [2]
            if filename[-1] == "D":
                jvType='dk'
            elif filename[-1] == "L":
                jvType = 'lt'
            self.dataDict = {'Path': path, 'Folder': folder, 'File': file, 'Solar Simulator': "PDIL substrate sim",
              'User Initials': user, 'Sample': sampleName,
              'Scan Direction': scanDir, 'LightDark': jvType}
            self.dataDF = self.dataDF.append(self.dataDict, ignore_index=True)
        
        except:
            print("File naming convention incompatible for" + self.filename +
                  ". Format should be " +
                  "<user>_<sampleName>_<rev/fwd>_*_<L/D>")
        # return self.dataNP, self.dataDict
    
    
    def STF136sup(self,filename):
        self.filename = filename
        # This version only supports data with light JV included.
        # If the file only contains dark JV, then it will generate NaN for what we want
        # I need to add in interpretation of the first two blocks of text, which tell us things like device area.
        # Sometimes STF136 appends multiple JV measurements to one file.
        # The following mmaps and regex expressions splits differen JV runs up
        # It currently selects for the first JV run's data, but that could be changed.
        with open(self.filename) as f:
            mf=mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            chunks=re.finditer(r'(^"Comments:".*?)(?=^"Comments:"|\Z)',mf,re.S | re.M)
            for i, chunk in enumerate(chunks, 1):
                with open('/path/{file,chonk}.csv'.format(file = self.filename,
                                                          chonk=i), 'w') as fout:
                    fout.write(chunk.group(1))    
        self.dataNP = pd.loadtxt(self.filename+'1.csv', skiprows=18, usecols = [0,1],
                              delimiter='\t', dtype=np.float64)
        try:
            split0 = self.filename.split('/') ### splitting off path from filename
            file = split0[-1]
            path = split0[0:-1]
            folder = split0[-2]
            split1 = split0[-1].split('.') ### splitting the string with . as a delimiter
            fileNameSplit = split1[0].split('_') #splitting again with _
            user = fileNameSplit[0]     # user initials is first col [0]
            sampleName = fileNameSplit[1]     # cell name is second col [1]
            scanDir = fileNameSplit[2]    # scan direction is the third [2]
            self.dataDict = {'Path': path, 'Folder': folder, 'File': file, 'Solar Simulator': "STF136 superstrate sim",
              'User Initials': user, 'Sample': sampleName,
              'Scan Direction': scanDir, 'LightDark': 'lt'}
            self.dataDF = self.dataDF.append(self.dataDict, ignore_index=True)
            
        except:
            print("File naming convention incompatible for" + self.filename +
                  ". Format should be " +
                  "<user>_<sampleName>_<rev/fwd>_*")
        # return self.dataNP, self.dataDict
    
    
    def STF204in(self,filename):
        self.filename = filename
        self.dataNP = loadtxt(filename, skiprows=18, delimiter='\t', dtype=np.float64)
        try:
            split0 = self.filename.split('/') ### splitting off path from filename
            file = split0[-1]
            path = split0[0:-1]
            folder = split0[-2]
            split1 = split0[-1].split('.') ### splitting the string with . as a delimiter
            fileNameSplit = split1[0].split('_') #splitting again with _
            user = fileNameSplit[0]     # user initials is first col [0]
            sampleName = fileNameSplit[1]     # cell name is second col [1]
    #                nCells = filenameSplit[2]   #how many cells in the module? (if ncells<2, it's a device)
            scanDir = fileNameSplit[-5]    # scan direction is the third [2]
            jvType = fileNameSplit[-4]    # jvType is fourth [3]
            loopNum = fileNameSplit[-3]    # loop number is the fifth [4]
            pixNum = fileNameSplit[-2]   # pixel letter is 6th [5]
            scanNum = fileNameSplit[-1]  # scan number is 7th [6]
            self.dataDict = {'Path': path, 'Folder': folder, 'File': file, 'Solar Simulator': "STF204 indoor light sim",
              'User Initials': user, 'Sample': sampleName, 'Pixel': pixNum,
              'Loop': loopNum, 'Scan': scanNum, 'Scan Direction': scanDir,
              'LightDark': jvType}
            self.dataDF = self.dataDF.append(self.dataDict, ignore_index=True)
        except:
            print("File naming convention for " + self.filename
                  + " incompatible. Should be "
                  + "<user>_<sampleName>_<rev/fwd>_<lt/dk>_lp<#>_"
                  + "<pixel>_<scan number>")
        # return self.dataNP, self.dataDict