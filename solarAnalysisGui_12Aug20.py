#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:51:50 2020

Pretty big differences from last Gui:
    1) option to run JV files from other than SERFC215
    2) separated into individual classes
    3) drop down menus that are automatically filled with loaded parameters
    4) input data from load file dialogue
    5) parameters CSV to categorize devices

    
Structure of GUI:
    Main Window - Load Data tab
        Load Files
            file load dialogue
            radio buttons
                1) SERF C215
                2) STF 136
                3) PDIL
                4) Indoor
                5) Outdoor
                6) Load old dataFrame (csv? pickle?)
            file failed to load (bad format) populated window
        Load parameters CSV
            parameters loaded populated window
            Merge Data (intersection, will delete unmatched samples in loaded table)
            Clear Table
    Main Window - Clean Data tab
        Merge Data (intersection, will delete unmatched samples in loaded table)
        Restore data to original loaded version (pre-merging parameters csv, 
                                                 pre-cleaning, pre-deleting
                                                 in tree view)
        Log of actions
        Data Tree
            View loaded data - Jsc and Voc
            NEEDED! - preview JV curves (option to save separately)
            Delete devices highlighted in tree view
        NEEDED! - remove outliers, remove devices by threshold Jsc
    Main Window - Plot Data tab
        
        
    
@author: rbramant
"""

import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk
import pandas as pd
import numpy as np
from jvFileLoader_12Aug20 import LoadData as ld
import matplotlib as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import SortAndPlotFunctions_12Aug20 as spf
from PIL import ImageTk,Image 


class PlotMethods:
    #starting a class for selecting specific parameters to plot from a tree view. Unused.
    __dfToPlot = pd.DataFrame()
    def __init__(self, master):
        self.master = master
        


class DataMethods:
    #Purpose: contain and manipulate master dataframes shared between tabs
    #below are class attributes - they stick around and persist through different instances of the class.
    #class attributes should never be accessed directly by other classes.
    __dfLoaded = pd.DataFrame() #original loaded data. keep around to restore if needed.
    __dfAdjusted = pd.DataFrame() #edited data. merged with parameters, etc.
    __dfParameters = pd.DataFrame() #loaded from parameters CSV. keep around to restore if needed
    __dfHyst = pd.DataFrame() #not fully implemented yet in a way I like - a dataframe that includes hysteresis data from JV curves (difference in performance based on scan direction)
    __numpyDf = pd.DataFrame()
    badFileList = ''
    # noisyCurveList = []
    def __init__(self, master):
        self.master = master
        self.filenameList = []
        self.filename = ''
    def loadData(self, solarSim):
        #this will initiate file dialogue
        #it will then call jvFileLoader and start loading and analyzing data
        #jvFileLoader fills dataFrame, which concats to class attribute dfLoaded
        self.filenameList = filedialog.askopenfilenames(initialdir="/Users/rbramant/Documents/Scripts/python/8-13GuiAnalysis/",
                                                  title = "Select Solar Sim Files to Load",
                                                  filetypes = (("txt", "*.txt"), ("all files","*.*")))
        # self.dfTemp, self.badFileTemp, self.noisyCurveTemp = loadDataFromFileManager(self.filenameList, solarSim)
        loader = ld()
        loader.loadDataFromFileManager(self.filenameList, solarSim)
        self.dfTemp = loader.df
        self.badFileTemp = loader.badFormatLoadList
        self.noisyCurveTemp = loader.noisyCurveLoadList
        DataMethods.badFileSetter(self,self.badFileTemp)
        # DataMethods.noisyCurveList = self.noisyCurveTemp
        DataMethods.__dfLoaded = pd.concat([DataMethods.__dfLoaded, self.dfTemp])
    def loadDataCSV(self, addDevices = False):
        self.addDevices = addDevices
        # print(str(self.addDevices))
        self.filename = filedialog.askopenfilename(initialdir="/Users/",
                                                        title="Select Parameter CSV files to Load",
                                                        filetypes = (("csv","*.csv"),
                                                                     ("all files","*.*")))
        loader = ld()
        loader.loadParametersFromFileManager(self.filename, self.addDevices)
        self.dfTemp = loader.df
        self.dfpTemp = loader.dfP
        self.badFileTemp = loader.badFormatLoadList
        if self.addDevices == True:
            #If you want to load pre-processed data from solar sims (including all JV data)
            #this adds your data directly to the __dfLoaded dataframe along with the JV-txtfile loaded data
            try:
                if 'Voc' in self.dfTemp:
                    DataMethods.__dfLoaded = pd.concat([DataMethods.__dfLoaded, self.dfTemp])
                else:
                    raise
            except: 
                errorMessage = ('Checked for Voc key, was not present.',
                                f'CSV {self.filename} does not contain '+
                                'JV data or are not formatted correctly')
                LoadDataModule.loadLogFill(self,errorMessage)
                        
        elif self.addDevices == False:
            #Allows you to load multiple CSVs with different parameters for the same samples without duplicating samples.
                DataMethods.__dfParameters = pd.concat([DataMethods.__dfParameters, self.dfpTemp])

        DataMethods.badFileSetter(self, self.badFileTemp)
    def dataFrameMerger(self): 
        #This method merges __dfLoaded (data loaded from solar sims) and __dfParameters (data loaded from csv to assign correlatable parameters to our data).
        # the "left" facing join will only retain the csv data that pertains to the samples in __dfLoaded.
        #if CSV contained data for devices not listed in __dfLoaded, and "add Devices" was checked "no", then those devices won't be included in the final dataframe.
        #rewerite this to accomodate levelled dataframe from CSV-loader - levels that stipulate whether to match or to insert.
        #^ not crucial, already partially implemented by "cols_to_use" below. More important for pixels in blade coating
        if DataMethods.__dfParameters.empty == False:
            # try:
                df1 = DataMethods.__dfLoaded.copy()
                df2 = DataMethods.__dfParameters.copy()
                mergeOn = list(df2['match'].columns.values)
                # addParameters = list(df2['add'].columns.values)
                df2 = df2.droplevel(0,axis=1)
            #remove a level of df2 and remove duplicate columns from df2
                cols_not_to_use = [i for i in list(df2.columns.values) if i in list(df1.columns.values) and i not in mergeOn]
                print(cols_not_to_use)
                df2 = df2.drop(columns = cols_not_to_use)
                dfTemp = pd.merge(df1, df2, on=mergeOn, how='left')
                                    # validate = 'm:1')
            # except: 
            #     CleanDataModule.cleanLogFill(self,('parameters data set has duplicate samples!',''))
        elif DataMethods.__dfParameters.empty == True:
            dfTemp = DataMethods.__dfLoaded.copy()
        DataMethods.__dfAdjusted = dfTemp
        DataMethods.__dfAdjusted.reset_index(inplace=True)
    def cleanJscFunct(self, jscLim=4):
        #this is supposed to delete device data if those devices got less than a threshold Jsc
        #threshold Jsc is either 4 (default) or set by user
        try:
            jscLimit = float(jscLim)
        except:
            exceptionText = f'Jsc Limit must be a number. {jscLim} is not a valid entry.'
            CleanDataModule.cleanLogFill(self, exceptionText)
        df = DataMethods.dataFrameAdjusted_get(self)
        indexJscLim = df[df['Jsc']<jscLimit].index #find indexes of rows that match the condition Jsc < jscLimit
        df = df.drop(indexJscLim)
        DataMethods.__dfAdjusted = df #redefine __dfAdjusted to not include eliminated rows (where Jsc < jscLimit)
        tempLength = str(len(indexJscLim))
        insertText=f'removed {tempLength} IV curves because Jsc was below {jscLim}'
        CleanDataModule.cleanLogFill(self,insertText) #tell user how many rows were removed from dataset
    def cleanOutliers(self,param, rmGrp, zScore):
        #FIX THIS to remove ridiculously high outliers. This was written by previous coder, RCB has not implemented it
        # this removed the lower outliers based on Z score. (lower is important since removing the best performing cells isn't useful UNLESS IT IS - FIX THIS!)
        df = DataMethods.dataFrameAdjusted_get(self)
        zScoreFl = float(zScore)  
        if rmGrp:
            #### groups the data by rmGrp then removes outliers. This can be used to remove the worst data points from each cell, or other group, independant of the data in the other groups
            df = df[df.groupby(rmGrp)[param].\
              transform(lambda x: (x.mean() - x) / x.std() < zScoreFl).eq(1)]
            dfRm = df[df.groupby(rmGrp)[param].\
              transform(lambda x: (x.mean() - x) / x.std() > zScoreFl).eq(1)]
        if not rmGrp:
            ##if no group is specified all the data is lumped togther, and lowest points across all treatments, fwd or rev, cells, etc are removed
            df = df[df[param].\
                    transform(lambda x: (x.mean() - x) / x.std() < zScoreFl).eq(1)]
            dfRm = df[df[param].\
                    transform(lambda x: (x.mean() - x) / x.std() > zScoreFl).eq(1)]
        tempLength = len(dfRm.index) 
        tempLength = str(tempLength)
        DataMethods.__dfAdjusted = df
        insertText=f'removed {tempLength} IV curves based on Zscore of{zScore}'
        CleanDataModule.cleanLogFill(insertText)
    def badFileSetter(self, badFileTempList):
        self.badFileTemp = badFileTempList
        if not self.badFileTemp:
            DataMethods.badFileList = ''
        else: DataMethods.badFileList = self.badFileTemp
    #   the below definitions access class attributes for other classes. getters, setters, destroyers
    def dataFrameDevices_get(self):
        self.dataFrameDevices = DataMethods.__dfLoaded.copy()
        return self.dataFrameDevices
    def dataFrameAdjusted_get(self):
        self.dataFrameForPlot = DataMethods.__dfAdjusted.copy()
        return self.dataFrameForPlot
    def dataFrameParameters_get(self):
        self.dataFrameCSVs = DataMethods.__dfParameters.copy()
        return self.dataFrameCSVs
    def dataFrameDevices_destroy(self):
        DataMethods.__dfLoader = pd.DataFrame()
    def dataFrameParameters_destroy(self):
        DataMethods.__dfParameters = pd.DataFrame()
    def dataFrameAdjusted_destroy(self):
        DataMethods.__dfAdjusted = pd.DataFrame()
    def dataFrameAdjusted_removeItem(self, *args):
        dfAdjustRemove = DataMethods.__dfAdjusted.copy()
        # print(args[0])
        for arg in args[0]:
            print(arg[0])
            print(arg[1])
            dfAdjustRemove = dfAdjustRemove[dfAdjustRemove[arg[0]]==arg[1]]
        indexNames = dfAdjustRemove.index
        DataMethods.__dfAdjusted.drop(indexNames, inplace=True)
        print("Data deleted")
    def dataFrameAdjusted_columns(self):
        columnsList = DataMethods.__dfAdjusted.columns.values.tolist()
        return columnsList
        

class LoadDataModule:
    #Load Data tab built in this class
    def __init__(self,master):
        self.master = master
        loadDataFileFrame = ttk.Frame(master)
        loadDataFileFrame.pack(pady=20)
        loadParFileFrame = ttk.Frame(master)
        loadParFileFrame.pack()
        
        logFrame = tk.Frame(master)
        logFrame.pack()
        dataLogFrame = tk.Frame(logFrame)
        dataLogFrame.pack(side=tk.LEFT)
        loadLogFrame = ttk.LabelFrame(logFrame, text='Files Failed to Load:')
        loadLogFrame.pack(side=tk.RIGHT)
        
        #radio buttons to select solar sim or old dataFrame
        SOLARSIMS = [
            ("SERFC215 racetrack sim", "SERFC215 racetrack sim"),
            ("STF136 superstrate sim", "STF136 superstrate sim"),
            ("PDIL large substrate sim","PDIL substrate sim"),
            # ("STF204 indoor light sim", "STF204 indoor light sim"), #commented out because it's definitely not ready
            ("Reload DataFrame Pickle", "reload DF")
            ]
        solarSimSelect = tk.StringVar(master)
        for i, (text, sim) in enumerate(SOLARSIMS, start=0):
            self.radioSim = tk.Radiobutton(loadDataFileFrame, text=text,
                                        variable=solarSimSelect,
                                        value=sim)
            self.radioSim.grid(row = i, column = 1, padx=10, pady=5, sticky=tk.W)
        
        self.loadData_button = tk.Button(loadDataFileFrame, text="Load Data", command= 
                                         lambda: [DataMethods.loadData(self,solarSimSelect.get()),
                                                  self.loadLogFill(DataMethods.badFileList),
                                                  self.loadLogDeviceList(),
                                                  self.loadLogParametersList()])
        self.loadData_button.grid(row=0,column=0,padx=10,rowspan=len(SOLARSIMS), sticky=tk.W)
        #load CSV parameters button
        
        addDeviceLabel = tk.Label(loadParFileFrame, text="Use CSV to Add Devices?")
        addDeviceLabel.grid(column=0, row=0, rowspan=2, sticky=tk.W)
        addDeviceSelect = tk.BooleanVar(master)
        ADDCSVDEVICE = [("Yes", True), ("No", False)]
        for i, (text, addDevice) in enumerate(ADDCSVDEVICE, start=0):
            self.radioCsv = tk.Radiobutton(loadParFileFrame, text=text, 
                                           variable=addDeviceSelect,
                                           value=addDevice)
            self.radioCsv.grid(row=i,column=1,padx=10,pady=5, sticky=tk.W)
        self.loadCSV_button = tk.Button(loadParFileFrame, text="Load Parameters CSV",
                                        command = lambda: [DataMethods.loadDataCSV(self,addDeviceSelect.get()),
                                                           self.loadLogFill(DataMethods.badFileList),
                                                           self.loadLogParametersList(),
                                                           self.loadLogDeviceList()])
        self.loadCSV_button.grid(row=0,column=2, rowspan=2, columnspan=2)

        logScrollY = tk.Scrollbar(logFrame)
        logScrollY.pack(side=tk.RIGHT, fill=tk.Y)
        
        logScrollX = tk.Scrollbar(logFrame, orient=tk.HORIZONTAL)
        logScrollX.pack(side=tk.BOTTOM, fill=tk.X)

        self.loadLog = tk.Text(loadLogFrame, width=100, height=6,
                           yscrollcommand=logScrollY, xscrollcommand = logScrollX,
                           wrap = tk.NONE)
        self.loadLog.configure(state='disabled')
        self.loadLog.pack(fill=tk.Y)
        
        deviceLogFrame = ttk.LabelFrame(dataLogFrame, text='Devices Loaded:')
        deviceLogFrame.pack(side=tk.LEFT)
        self.loadDevList = tk.Listbox(deviceLogFrame, width=25,height=5,
                                        yscrollcommand=logScrollY)
        self.loadDevList.pack(fill=tk.BOTH)
        paramLogFrame = ttk.LabelFrame(dataLogFrame, text='Parameters Loaded:')
        paramLogFrame.pack(side=tk.RIGHT)
        
        self.loadParametersList = tk.Listbox(paramLogFrame,width=25,height=5,
                                      yscrollcommand=logScrollY)
        self.loadParametersList.pack(side = tk.LEFT, fill=tk.BOTH)

        self.loadCsvParametersList = tk.Listbox(paramLogFrame,width=25,height=5,
                                      yscrollcommand=logScrollY)
        self.loadCsvParametersList.pack(side = tk.RIGHT, fill=tk.BOTH)
        
        self.deleteFrame = tk.Frame(master)
        self.deleteFrame.pack()
        self.deleteLoadedData = tk.Button(self.deleteFrame, text="Delete Loaded Devices",
                                          command=lambda: [DataMethods.dataFrameDevices_destroy(self),
                                                           self.loadLogDeviceList(),
                                                           self.loadLogFill(('','Devices Deleted'))])
        self.deleteLoadedParams = tk.Button(self.deleteFrame, text='Delete Loaded Parameters',
                                            command = lambda:[DataMethods.dataFrameParameters_destroy(self),
                                                              self.loadLogParametersList(),
                                                              self.loadLogFill(('','Parameters Deleted'))])
        self.deleteLoadedData.grid(column=0,row=0)
        self.deleteLoadedParams.grid(column=1,row=0)
        
            
    def loadLogFill(self, insertList):
        self.loadLog.configure(state='normal')
        for i in insertList:
            self.loadLog.insert('end+2l', f'{i}\n')
        self.loadLog.configure(state='disabled')
    
    def loadLogParametersList(self):
        self.deviceDF = DataMethods.dataFrameDevices_get(self)
        self.loadParametersList.configure(state='normal')
        self.loadParametersList.delete(0,tk.END)
        for i in self.deviceDF.columns:
            self.loadParametersList.insert(tk.END,str(i))
        self.loadParametersList.configure(state='disabled')
        
        self.csvDF = DataMethods.dataFrameParameters_get(self)
        self.loadCsvParametersList.configure(state='normal')
        self.loadCsvParametersList.delete(0,tk.END)
        for i in self.csvDF.columns:
            self.loadCsvParametersList.insert(tk.END,str(i))
        self.loadCsvParametersList.configure(state='disabled')
        
        
    def loadLogDeviceList(self):
        self.deviceDF = DataMethods.dataFrameDevices_get(self)
        # updateListDevices = self.deviceDF['Sample'].values
        # self.listDevices.set(updateListDevices)
        self.loadDevList.configure(state='normal')
        self.loadDevList.delete(0,tk.END)
        if 'Number of Cells' in self.deviceDF.columns:
            for index, row in self.deviceDF.iterrows():
                self.loadDevList.insert(tk.END,
                                        str(row['User Initials'])+" "+
                                        str(row['Sample'])+" "+
                                        str(row['Number of Cells']))
                                        # str(row['Scan'])+" "+
                                        # str(row['Scan Direction']))
            
        if 'Pixel' in self.deviceDF.columns:
            for index, row in self.deviceDF.iterrows():
                self.loadDevList.insert(tk.END,
                                        str(row['User Initials'])+" "+
                                        str(row['Sample'])+" "+
                                        str(row['Pixel']))
                                        # str(row['Scan'])+" "+
                                        # str(row['Scan Direction']))
        else:
            for index, row in self.deviceDF.iterrows():
                self.loadDevList.insert(tk.END,
                                        str(row['User Initials'])+" "+
                                        str(row['Sample']))
        self.loadDevList.configure(state='disabled')


# class ParametersModule:
#     def __init__(self, master):
#         self.master = master
#         self.loadFileFrame = tk.Frame(master)
#         self.loadFileFrame.pack()
#         self.loadCSV_button = tk.Button(self.loadFileFrame, text="Load Parameters CSV",
#                                         command = lambda: ParametersModule.loadParameters(self))
#         self.loadCSV_button.pack()
    
    
#     def loadParameters(self):
#         #in reality, this will initiate file open dialogue
#         #it will then merge DataFrames with the load Data dataframe
#         print("open select file dialogue for parameters csv")


class CleanDataModule:
    #needs to
    #   a) merge CSV parameters dataframe and solarSim loaded dataframes X
    #   b) button to restore to original dataframes X
    #   c) save current dataframe to a storage file
    #   d) calculate hysteresis
    #       filter by samples that have both reverse and forward scan directions
    #       calculate hysteresis and write new columns for PCE_hyst, FF_hyst, Jsc_hyst, Voc_hyst
    #   e) remove outliers
    #   f) filter by Jsc lower limit X
    #   g) remove individual devices/pixels/scans (with drop-down menus or treeview?) X
    #   h) preview JV curves and potentially save them
    def __init__(self, master):
        self.master = master
        masterFrame = ttk.Frame(master)
        masterFrame.pack()
        manipDataFileFrame = ttk.Frame(masterFrame)
        manipDataFileFrame.grid(column=0,row=0)
        cleanDataFrame = ttk.Frame(masterFrame)
        cleanDataFrame.grid(column=0,row=1)
        logFrame = ttk.Labelframe(masterFrame, text="Activity Log")
        logFrame.grid(column=0,row=10)
        viewDataFrame = ttk.Labelframe(masterFrame, text = "Select Devices to Delete")
        viewDataFrame.grid(column=1,row=10)
        
        #entries:
        jscLim = tk.StringVar()
        jscLowerLimLabel1 = tk.Label(cleanDataFrame, text=f'Jsc Lower Limit:')
        jscLowerLimLabel1.grid(column=0,row=2)
        jscLowerLimLabel2 = tk.Label(cleanDataFrame, text=f'mA/cm\N{SUPERSCRIPT TWO}')
        jscLowerLimLabel2.grid(column=2,row=2)
        jscLowerLimEntry = tk.Entry(cleanDataFrame, textvariable=jscLim, width = 5)
        jscLowerLimEntry.grid(column=1,row=2)
        
        
        mergeScrollY = tk.Scrollbar(logFrame)
        mergeScrollY.grid(column=10,row=1)
        
        self.cleanLoadLog=tk.Text(logFrame,width=40,height=5,yscrollcommand=mergeScrollY,
                                  wrap = tk.WORD)
        self.cleanLoadLog.grid(column=0,row=1,rowspan=2)
        self.cleanLoadLog.configure(state='disabled')
        
        self.viewDataTree = ttk.Treeview(viewDataFrame, height = 5,
                                         selectmode='extended', show = 'tree headings')
        self.viewDataTree["columns"]=('User Initials', 'Sample', 'Pixel',
                                      'Scan', 'Scan Direction', 'PCE', 'Jsc')
        self.viewDataTree['displaycolumns'] = (3,4,5,6)
        self.viewDataTree.pack()
        self.viewDataTree.column("#0", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("User Initials", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("Sample", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("Pixel", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("Scan", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column('Scan Direction', width = 100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("PCE", width=100, minwidth=50, stretch=tk.YES)
        self.viewDataTree.column("Jsc", width=100, minwidth=50, stretch = tk.YES)
        self.viewDataTree.heading("#0", text= "Sample")
        self.viewDataTree.heading("Scan", text = 'Scan #')
        self.viewDataTree.heading('Scan Direction', text = 'fwd/rev')
        self.viewDataTree.heading('PCE', text="PCE (%)")
        self.viewDataTree.heading('Jsc', text=f'Jsc'
                                  + f'(mA/cm\N{SUPERSCRIPT TWO})')

        #buttons:
        self.deleteDevicesButton = tk.Button(viewDataFrame, text = 'Delete Selected Devices',
                                             command = lambda: CleanDataModule.destroyTreeItems(self))
        self.deleteDevicesButton.pack()

        self.mergeFrameButton = tk.Button(manipDataFileFrame, text='Merge Parameters with JV Data',
                                          command= lambda:[DataMethods.dataFrameMerger(self),
                                                           CleanDataModule.cleanLogFill(self,('DataFrames Merged')),
                                                           CleanDataModule.populateDataTree(self)])
        self.mergeFrameButton.grid(column=0,row=0)
        
        self.startOver = ttk.Button(manipDataFileFrame, text='Start Over',
                                    command = lambda: [DataMethods.dataFrameAdjusted_destroy(self),
                                                       DataMethods.dataFrameMerger(self),
                                                       CleanDataModule.cleanDataTree(self),
                                                       CleanDataModule.populateDataTree(self),
                                                       CleanDataModule.cleanLogFill(self,'Data restored to original')])
        self.startOver.grid(column=0,row=1)
        
        self.cleanJscButton = ttk.Button(cleanDataFrame, text='Remove Jsc Below Limit^',
                                         command = lambda: [DataMethods.cleanJscFunct(self,jscLowerLimEntry.get()),
                                                            CleanDataModule.cleanDataTree(self),
                                                            CleanDataModule.populateDataTree(self)])
        self.cleanJscButton.grid(column=0,row=3, columnspan=3)
     
    def previewJVplot(self):
        #write here
        print('JV plot preview')
        
    def populateDataTree(self):
        self.__treeData = DataMethods.dataFrameAdjusted_get(self)
        sampleGroup = self.__treeData.groupby(by=['User Initials','Sample'], as_index=False)
        for name, group in sampleGroup:
            newNode = self.viewDataTree.insert('',1,text=name[0]+' '+name[1],
                                            values=(group['User Initials'],group['Sample'],
                                                    '','','',group['PCE'].mean(),
                                                    group['Jsc'].mean()))
            # for row in group.dropna(axis='index',subset=['Pixel']).itertuples():
            pixelGroup = group.groupby(by='Pixel', as_index=False)
            for pname, pgroup in pixelGroup:
                newNodeP = self.viewDataTree.insert(newNode,'end',text=pname,
                                         values = (pgroup['User Initials'],pgroup['Sample'],
                                                   pgroup['Pixel'],'','', pgroup['PCE'].mean(), pgroup['Jsc'].mean()))
                # print(pname, pgroup)
                for row_index, row in pgroup.iterrows():
                    # print(row_index, row)
                    self.viewDataTree.insert(newNodeP, 'end',
                                              values=(row['User Initials'],row['Sample'],
                                                      row['Pixel'],row['Scan'],
                                                      row['Scan Direction'],
                                                      row['PCE'], row['Jsc']))
    def cleanDataTree(self):
        self.viewDataTree.delete(*self.viewDataTree.get_children())
        
    def destroyTreeItems(self):
        self.selectedItems = self.viewDataTree.selection()
        print(self.selectedItems)
        self.attributeList = []
        columnvalues = self.viewDataTree['columns']
        counter = 0
        # print(columnvalues)
        for i in self.selectedItems:
            children = self.viewDataTree.get_children(i)
            print(children)
            if len(children) > 0:
                for j in children:
                    self.attributeList = []
                    deviceValues = self.viewDataTree.item(j, 'values')
                    for k, value in enumerate(deviceValues,start=0):
                        self.attributeList.append((columnvalues[k], value))
                    DataMethods.dataFrameAdjusted_removeItem(self,self.attributeList[0:5])
                    self.viewDataTree.delete(j)
                    counter += 1
                # self.viewDataTree.delete(self.viewDataTree.parent(children[0]))
            else:
                self.attributeList = []
                deviceValues = self.viewDataTree.item(i, 'values')
                for k, value in enumerate(deviceValues,start=0):
                    self.attributeList.append((columnvalues[k], value))
                DataMethods.dataFrameAdjusted_removeItem(self,self.attributeList[0:5])
                self.viewDataTree.delete(i)
                # self.viewDataTree.delete(self.viewDataTree.parent(i))
                counter += 1
                
        # print(self.attributeList)
        # self.viewDataTree.delete(*)
        CleanDataModule.cleanDataTree(self)
        CleanDataModule.populateDataTree(self)
        CleanDataModule.cleanLogFill(self,f'{counter} devices deleted from dataframe')
                
    def cleanLogFill(self, insertText):
        self.cleanLoadLog.configure(state='normal')
        self.cleanLoadLog.insert('end+2l', f'{insertText}\n')
        self.cleanLoadLog.configure(state='disabled')
        
        

class PlotDataModule:
    # A window where you can:
    #   a) Select which variables you want to plot (categories, split into three sections by color and "dots")
    #   b) Determine y range of data, overall size of plot
    #   c) "Preview" plot
    #   d) save plot as: <your choice of title>
    #   e) types of plots:
    #       bar plot
    #       strip plot
    #       box plot
    #       stats plot
    def __init__(self, master):
        self.master = master
        #Variables:
        self.xVar1 = tk.StringVar(self.master)
        self.xVar1.set('')
        self.xVar2 = tk.StringVar(self.master)
        self.xVar2.set('')
        self.xVarDot = tk.StringVar(self.master)
        self.xVarDot.set('')
        self.yVar = tk.StringVar(self.master)
        self.yVar.set('')
        self.plotTitle = '[no plot title]'
        self.sizeX = 5
        self.sizeY = 5
        self.fntSz = 1
        self.yAxRangeMin = tk.DoubleVar()
        self.yAxRangeMax = tk.DoubleVar()
        SCANDIRSET = ['rev', 'fwd', 'both']
        self.scanDirection = tk.StringVar(master)
        self.scanDirection.set('both')
        self.yVars = ['FF', 'PCE', 'Jsc', 'Voc', 'Jmpp', 'Vmpp', 'Rsh', 'Rs', 'FF Hyst', 'PCE Hyst', 'Jsc Hyst', 'Voc Hyst',
                      'Jmpp Hyst', 'Vmpp Hyst', 'Rs Hyst', 'Rsh Hyst']
        self.yPairPlotList = tk.StringVar()
        
        #Frames:
        setupFrame = ttk.Frame(self.master)
        setupFrame.pack()
        self.plotPreviewFrame = ttk.Frame(self.master)
        self.plotPreviewFrame.pack(padx=0,pady=0)
        previewFrame = ttk.Frame(setupFrame)
        previewFrame.grid(column=1,row=2)
        self.editPlotSetupFrame = ttk.Frame(setupFrame)
        self.editPlotSetupFrame.grid(column=1,row=0)
        self.pairPlotSetupFrame = ttk.Labelframe(setupFrame, text='Pair Plot')
        self.pairPlotSetupFrame.grid(column=0,row=0,rowspan=10, sticky=tk.N)
        self.plotPreviewSetupFrame = ttk.Frame(previewFrame)
        self.plotPreviewSetupFrame.pack(padx=10,pady=10)
        self.plotPreviewFrame = ttk.Frame(self.master)
        self.plotPreviewFrame.pack(padx=5,pady=5, expand=True, fill=tk.BOTH)
        
        #Labels:
        self.yVarLabel = ttk.Label(self.editPlotSetupFrame, text="Y Variable")
        self.yVarLabel.grid(column = 1,row=1, sticky=tk.E)
        self.yVarMinLabel = ttk.Label(self.editPlotSetupFrame, text = 'Y Minimum')
        self.yVarMinLabel.grid(column=1,row=2,sticky=tk.E)
        self.yVarMaxLabel = ttk.Label(self.editPlotSetupFrame, text='Y Maximum')
        self.yVarMaxLabel.grid(column=1,row=3,sticky=tk.E)
        self.sizeXlabel = ttk.Label(self.editPlotSetupFrame, text='plot size x')
        self.sizeXlabel.grid(column=1,row=4, sticky=tk.E)
        self.sizeYlabel = ttk.Label(self.editPlotSetupFrame, text='plot size y')
        self.sizeYlabel.grid(column=1,row=5, sticky=tk.E)
        self.xVar1Label = ttk.Label(self.editPlotSetupFrame, text='X Category 1')
        self.xVar1Label.grid(column=3, row=1, sticky=tk.E)
        self.xVar2Label = tk.Label(self.editPlotSetupFrame, text='X Category 2')
        self.xVar2Label.grid(column=3, row=2, sticky=tk.E)
        self.xVarDotLabel = tk.Label(self.editPlotSetupFrame, text='X Dots Category')
        self.xVarDotLabel.grid(column=3,row=3, sticky=tk.E)
        self.sizeFntLabel = ttk.Label(self.editPlotSetupFrame, text='Font Size')
        self.sizeFntLabel.grid(column=3,row=4,sticky=tk.E)
        self.xVar1Selected = tk.Label(self.editPlotSetupFrame,textvariable=self.xVar1, width=10, fg='green')
        self.xVar1Selected.grid(column=5,row=1)
        self.xVar2Selected = tk.Label(self.editPlotSetupFrame,textvariable=self.xVar2, width=10, fg='green')
        self.xVar2Selected.grid(column=5,row=2)
        self.xVarDotSelected = tk.Label(self.editPlotSetupFrame,textvariable=self.xVarDot, width=10, fg='green')
        self.xVarDotSelected.grid(column=5,row=3)
        
        #Entries:
        self.yVarMin = ttk.Entry(self.editPlotSetupFrame, width=5)
        self.yVarMin.grid(column=2,row=2, sticky=tk.W)
        self.yVarMin.insert(tk.END, '0')
        self.yVarMax = ttk.Entry(self.editPlotSetupFrame, width=5)
        self.yVarMax.grid(column=2,row=3, sticky=tk.W)
        self.yVarMax.insert(tk.END,'0')
        self.sizeXentry= ttk.Entry(self.editPlotSetupFrame,width=5)
        self.sizeXentry.grid(column=2,row=4, sticky=tk.W)
        self.sizeXentry.insert(tk.END, '5')
        self.sizeYentry = ttk.Entry(self.editPlotSetupFrame, width=5)
        self.sizeYentry.grid(column = 2, row=5, sticky=tk.W)
        self.sizeYentry.insert(tk.END,'5')
        self.sizeFntEntry = ttk.Entry(self.editPlotSetupFrame, width=5)
        self.sizeFntEntry.grid(column=4,row=4,sticky=tk.W)
        self.sizeFntEntry.insert(tk.END, '1')
        
        
        #Drop Menus and Listboxes:
        self.xVar1DropMenu = ttk.OptionMenu(self.editPlotSetupFrame, self.xVar1, '')
        self.xVar1DropMenu.configure(width=10)
        self.xVar1DropMenu.grid(column = 4, row=1, padx=0)
        
        self.xVar2DropMenu = ttk.OptionMenu(self.editPlotSetupFrame, self.xVar2, '')
        self.xVar2DropMenu.configure(width=10)
        self.xVar2DropMenu.grid(column=4,row=2, padx=0)
        
        self.xVarDotDropMenu = ttk.OptionMenu(self.editPlotSetupFrame,self.xVarDot, '')
        self.xVarDotDropMenu.configure(width=10)
        self.xVarDotDropMenu.grid(column=4,row=3, padx=0)
        
        self.yVarDropMenu = ttk.OptionMenu(self.editPlotSetupFrame, self.yVar, self.yVars[0], *self.yVars)
        self.yVarDropMenu.configure(width=5)
        self.yVarDropMenu.grid(column = 2, row=1,padx=0)
        #below list plot is supposed to allow you to select particular variables to compare in the pair plot
        #it doesn't work yet
        self.yVarPairLabel = ttk.Label(self.pairPlotSetupFrame, text="Select Variables")
        self.yVarPairLabel.grid(column=0,row=0)
        self.yPairPlotList.set(['PCE', 'Voc', 'Jsc','FF'])
        self.yVarPairList = tk.Listbox(self.pairPlotSetupFrame, selectmode=tk.MULTIPLE,
                                       width=10, listvariable=self.yPairPlotList)
        for i, string in enumerate(self.yVars):
            self.yVarPairList.insert(i, string)
        self.yVarPairList.grid(column=0, row = 1, padx=10)
        self.yVarPairList.configure(state=tk.DISABLED)
        
        #Buttons and Radio Buttons:
        self.updateButton = tk.Button(self.editPlotSetupFrame, text='Reset X', width=10,
                                      command=lambda: [self.updateVariables()])
        self.updateButton.grid(column=5, row=0, padx=0)
        self.boxPlotButton = tk.Button(self.plotPreviewSetupFrame, text='Box Plot Preview',
                                       command= lambda:[self.previewPlot(self.plotPreviewFrame, 'box')])
        self.boxPlotButton.grid(column=0, row=0, padx=10)
        self.stripPlotButton = tk.Button(self.plotPreviewSetupFrame, text='Strip Plot Preview',
                                         command = lambda:self.previewPlot(self.plotPreviewFrame,'strip'))
        self.stripPlotButton.grid(column=1,row=0, padx=10)
        self.pairPlotButton = tk.Button(self.pairPlotSetupFrame, text= 'Generate Pair Plot',
                                        command = lambda: self.previewPlot(self.plotPreviewFrame,'pair'))
        self.pairPlotButton.grid(column=0,row=10, padx=10)
        
        for i, text in enumerate(SCANDIRSET, start=0):
            self.radioScanDir = tk.Radiobutton(self.editPlotSetupFrame, text=text,
                                        variable=self.scanDirection,
                                        value=text)
            self.radioScanDir.grid(row = 1+i, column = 6, padx=10, pady=5, sticky=tk.W)
        #canvas
        xScrollPreview = tk.Scrollbar(self.plotPreviewFrame, orient=tk.HORIZONTAL)
        xScrollPreview.pack(side=tk.BOTTOM, expand=True, fill=tk.X)
        yScrollPreview = tk.Scrollbar(self.plotPreviewFrame, orient=tk.VERTICAL)
        yScrollPreview.pack(side=tk.RIGHT, expand=True, fill=tk.Y)
        self.preview = tk.Canvas(self.plotPreviewFrame, 
                                 width = 900, height=400,
                                 scrollregion=(0,0,1000,1500),
                                 xscrollcommand = xScrollPreview.set,
                                 yscrollcommand = yScrollPreview.set)
        yScrollPreview.config(command=self.preview.yview)
        xScrollPreview.config(command=self.preview.xview)
        self.preview.pack(expand=True, side = tk.LEFT, fill=tk.BOTH)
        self.preview.configure(state = 'disabled')
        
    def previewPlot(self, master, plotType):  
        self.plotType = plotType
        self.master = master
        yGroup = self.yVar.get()
        x1Group, x2Group, x2DotGroup = self.xVar1.get(), self.xVar2.get(), self.xVarDot.get()
        yAxRangeMin, yAxRangeMax = self.yVarMin.get(), self.yVarMax.get()
        sizeX, sizeY = self.sizeXentry.get(), self.sizeYentry.get()
        fntSize = self.sizeFntEntry.get()
        try:
            yAxRangeMin, yAxRangeMax = float(yAxRangeMin), float(yAxRangeMax)
            sizeX, sizeY = float(sizeX), float(sizeY)
            fntSize = float(fntSize)
        except:
            print('Entries for y axis range and figure size must be numeric')
        self.df = DataMethods.dataFrameAdjusted_get(self)
        if self.scanDirection.get() == 'fwd':
            self.df = self.df.loc[self.df['Scan Direction']=='fwd']
        elif self.scanDirection.get() == 'rev':
            self.df = self.df.loc[self.df['Scan Direction']=='rev']
        newPlot = spf.Plots(self.master, x1Group=x1Group, x2Group=x2Group,
                         x2DotGroup=x2DotGroup, sizeX=sizeX, sizeY=sizeY,
                         yAxRangeMin=yAxRangeMin, yAxRangeMax=yAxRangeMax, fntSz=fntSize,
                         df=self.df, yGroup=yGroup)
        if plotType=='box':
            plotImage=newPlot.barPlot()
        elif plotType == 'strip':
            plotImage = newPlot.stripPlot()
        elif plotType == 'pair':
            plotImage = newPlot.pairPlot()
            print('Pair Plot Generated')
        photo = ImageTk.PhotoImage(plotImage, master=self.master)
        self.preview.configure(state = 'normal')
        self.preview.delete('all')
        self.preview.create_image(0,0,anchor = tk.NW, image=photo)
        self.preview.image = photo
        self.preview.configure(state = 'disabled')
        print('plot updated')
        
    def updateVariables(self):
        self.df = DataMethods.dataFrameAdjusted_get(self)
        if self.scanDirection.get()=='reverse':
            self.df = self.df.loc['Scan Direction'=='rev']
        elif self.scanDirection.get()=='forward':
            self.df = self.df.loc['ScanDirection'=='fwd']
        yVars = ['Path', 'File', 'index']
        yVars.extend(self.yVars)
        # print(yVars)
        self.listVariables = self.df.columns.values.tolist()
        # print(self.listVariables)
        self.listVariables = set(self.listVariables) - set(yVars)
        # print(self.listVariables)
        # self.xVar1DropMenu.set_menu(*self.listVariables)
        # print(DataMethods.dataFrameAdjusted_get(self))
        menu1 = self.xVar1DropMenu['menu']
        menu1.delete(0, "end")
        self.xVar1.set('')
        menu2 = self.xVar2DropMenu['menu']
        menu2.delete(0, "end")
        self.xVar2.set('')
        menuDot = self.xVarDotDropMenu['menu']
        menuDot.delete(0, 'end')
        self.xVarDot.set('')
        for string in self.listVariables:
            menu1.add_command(label=string, 
                              command=tk._setit(self.xVar1, string))
            menu2.add_command(label=string, 
                              command=tk._setit(self.xVar2, string))
            menuDot.add_command(label=string,
                              command=tk._setit(self.xVarDot, string))


class NotebookWindow:
     def __init__(self, master):
        self.master = master
         
        mainNb = ttk.Notebook(master, padding = 10, width = 1000)
        mainNb.pack()
        
        f1 = ttk.Frame(self.master)
        mainNb.add(f1, text="Load Data")
        LoadDataModule(f1) 
        
        # f2 = ttk.Frame(self.master)
        # mainNb.add(f2, text = "Load Parameters")
        # ParametersModule(f2)
        
        f3 = ttk.Frame(self.master)
        mainNb.add(f3, text="Clean Data")
        CleanDataModule(f3)
        
        f4 = ttk.Frame(self.master)
        mainNb.add(f4, text="Plot Data")
        PlotDataModule(f4)
        

class MainWindow:
    def __init__(self, master):
        self.master = master
        master.title("TPV Data Analysis GUI")

        # self.label = tk.Label(master, text="TPV Data Analysis GUI")
        # self.label.pack()
        self.close_button = tk.Button(master, text="Close", command=master.quit)
        self.close_button.pack()
        NotebookWindow(self.master)
        
root = tk.Tk()
my_gui = MainWindow(root)
root.update_idletasks()
root.mainloop()
