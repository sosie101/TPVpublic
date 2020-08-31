#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 12:47:33 2020

@author: rbramant
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy import optimize, stats
from scipy.stats import linregress
import csv
import PIL.Image, PIL.ImageTk

class ScanDirections:
    def __init__(self, df):
        self.dfNorm = df
        self.dfHyst = self.dfNorm.copy()
        self.columnList = []
    def calcHysteresis(self):
        # take dataframeAdjusted and calculate an identical dfHyst dataframe, where JV parameters have been calculated for hysteresis
        # do I automatically run this for every dataframe, or only when the user requests it?
        # do we assign the new dataframe to dfAdjusted with new columns ('FF Hyst', etc), or do we create a separate dataframe that only gets called when "hyst" is requested?
        # the first is probably better for  eventual SQL storage
        def hystFunc(df):
            if {'rev','fwd'}.issubset(df.index):
                scalar = abs(df.loc['rev'].mean() - df.loc['fwd'].mean())
            else:
                scalar = np.NaN
            return scalar
        
        if 'Pixel' in self.dfHyst.columns:
            self.columnList = ['User Initials', 'Sample', 'Pixel', 'Loop', 'Scan']
        elif 'Loop' in self.dfHyst.columns:
            self.columnList = ['User Initials', 'Sample', 'Loop', 'Scan']
        else:
            self.columnList = ['User Initials', 'Sample', 'Scan']
        # self.dfHyst.set_index([i for i in self.columnList], inplace=True, drop=False)
        self.dfHyst.set_index(['Scan Direction'], inplace=True, drop=False)
        # print(self.dfHyst)
        self.dfHyst['PCE Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['PCE'].transform(lambda x: hystFunc(x))
        self.dfHyst['FF Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['FF'].transform(lambda x: hystFunc(x))
        self.dfHyst['Jsc Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Jsc'].transform(lambda x: hystFunc(x))
        self.dfHyst['Voc Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Voc'].transform(lambda x: hystFunc(x))
        self.dfHyst['Jmpp Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Jmpp'].transform(lambda x: hystFunc(x))
        self.dfHyst['Vmpp Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Vmpp'].transform(lambda x: hystFunc(x))
        self.dfHyst['Rs Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Rs'].transform(lambda x: hystFunc(x))
        self.dfHyst['Rsh Hyst']= self.dfHyst.groupby(by=self.columnList, as_index=False)['Rsh'].transform(lambda x: hystFunc(x))
        # print(self.dfHyst['PCE Hyst'])
        self.dfHyst.reset_index(inplace=True, drop=True)
        # return self.dfHyst.copy()
        
class Plots:
    def __init__(self, master, x1Group, x2Group, x2DotGroup, sizeX, sizeY,
                 yAxRangeMin, yAxRangeMax, fntSz, df, yGroup):
        self.master = master
        self.x1Group = x1Group
        self.x2Group = x2Group
        self.x2DotGroup = x2DotGroup
        self.sizeX = sizeX
        self.sizeY = sizeY
        self.YaxRangeMin = yAxRangeMin
        self.YaxRangeMax = yAxRangeMax
        # print(self.YaxRangeMin+' '+self.YaxRangeMax)
        self.fntSz = fntSz
        self.df = df
        self.yGroup = yGroup
        self.strSave = 'testing.png'
        self.folderSave = 'data/'
        self.title1Group = ''
        self.title2Group = ''
        self.titleDotGroup = ''
        for string in self.x1Group.split(' '):
            self.title1Group += string
        for string in self.x2Group.split(' '):
            self.title2Group += string
        for string in self.x2DotGroup.split(' '):
            self.titleDotGroup += string
        #account for 'could not convert to float' on an empty entry
        if self.YaxRangeMin == "":
                self.YaxRangeMin = 0.0
        else:
                self.YaxRangeMin = float(self.YaxRangeMin)
        if self.YaxRangeMax == "":
                self.YaxRangeMax = 0.0
        else:
                self.YaxRangeMax = float(self.YaxRangeMax)
        if self.sizeX == "":
                self.sizeX = 5.0
        else:
                self.sizeX = float(self.sizeX)
        if self.sizeY == "":
                self.sizeY = 5.0
        else:
                self.sizeY = float(self.sizeY)
                
    def barPlot(self):
        # print(self.x1Group, self.x2Group, self.x2DotGroup)
        sns.set(font_scale=self.fntSz)
        if self.x1Group and not self.x2Group:
            plt.figure()
            ax1 = sns.boxplot(x=self.x1Group, y=self.yGroup, notch = False,
                            #hue_order=clarity_ranking,
                            data=self.df)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            ax1.set_xticklabels(ax1.get_xticklabels(), rotation=30, ha="right")
            self.strSave = "boxPlot" + self.yGroup + self.title1Group + ".png"
            titleSave = self.yGroup + " as a function of " + self.x1Group
            ax1.set_title(titleSave)
            ########## sizing plot, adjusting bottom margin for long axis labels
            sns.set(rc={'figure.figsize':(self.sizeX,self.sizeY)}) ######
            plt.subplots_adjust(bottom=0.2)
            plt.subplots_adjust(right=0.8)
               
            if self.x2DotGroup: #### if the user specfied anything for X2DotGroup, the data points will be superimposed over the box plts
                if self.x2DotGroup != self.x1Group:   #### this adds more information to the plot, as you can now label 2 groups (or have 2 independent variables) in the plot
                    #happy with how this looks
                    ax1 = sns.swarmplot(x=self.x1Group, y=self.yGroup, hue = self.x2DotGroup,palette="bright",
                                        data=self.df, size=6, color=".5", linewidth=2,dodge=True)
                elif self.x2DotGroup == self.x1Group: ###
    #                ax1 = sns.swarmplot(x=X1Group, y=yGroup, data=df,
    #                size=5, color=".1", linewidth=0)
                    ## happy with how this plot looks
                    ax1 = sns.swarmplot(x=self.x1Group, y=self.yGroup,hue = self.x2DotGroup, palette="bright",
                                        data=self.df, size=2, color=".01", linewidth=4,dodge=True)
    #                ax1 = sns.swarmplot(x=X1Group, y=yGroup,hue = X2DotGroup,palette="muted", data=df,
    #                size=8, color=".5", linewidth=2,dodge=True)
                ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        
        elif self.x1Group and self.x2Group:
            plt.figure()
            ax1 = sns.boxplot(x=self.x1Group, y=self.yGroup, hue=self.x2Group,
                            palette="muted", notch = False, #hue_order=clarity_ranking,
                            data= self.df)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            ax1.set_xticklabels(ax1.get_xticklabels(), rotation=30, ha="right")
            self.strSave = "boxPlot" + self.yGroup + self.title1Group + self.title2Group + ".png"
            ###### sizing plot, adjusting bottom margin for long axis labels
            sns.set(rc={'figure.figsize':(self.sizeX,self.sizeY)}) ######
            plt.subplots_adjust(bottom=0.2)
            plt.subplots_adjust(right=0.8)
            #######
            titleSave = self.yGroup + " as a function of " + self.x1Group + " and " + self.x2Group# + " scan direction = " + strFwdRev
            ax1.set_title(titleSave)
            #colr = sns.color_palette("RdGy", 2)
            
    #        ax1 = sns.swarmplot(x=X1Group, y=yGroup, hue=X2DotGroup, palette="RdGy",dodge=True, data=df,  #### hardcoding in hue for testing
    #        size=7, color=".3", linewidth=0)
            
            #### need to move the legends
            if self.x2DotGroup:
                if self.x2DotGroup != self.x2Group: #### this adds more information to the plot, as you can now label 3 groups (or have 3 independent variables) in the plot
                    ax1 = sns.swarmplot(x=self.x1Group, y=self.yGroup,hue = self.x2DotGroup,palette="bright", data=self.df,
                    size=6, color=".5", linewidth=2,dodge=True)
                    ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
                elif self.x2DotGroup==self.x2Group:
                    #colour = sns.palplot(sns.cubehelix_palette(dark=0, light=.95))
                    ax1 = sns.swarmplot(x=self.x1Group, y=self.yGroup, hue = self.x2DotGroup,
                                        palette="bright", data=self.df, size=2,
                                        color=".01", linewidth=4,dodge=True)
                    ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        if self.YaxRangeMin != 0 or self.YaxRangeMax != 0:
        #### converting the axis scalling to float
            # print(self.YaxRangeMin, self.YaxRangeMax)
            # ax1.set(ylim=(self.YaxRangeMin,self.YaxRangeMax))
            plt.ylim(self.YaxRangeMin, self.YaxRangeMax)
            # print('resizing axis')
        plt.tight_layout()
        plt.savefig(self.folderSave + self.strSave)
        # plt.close()
        plotImage = PIL.Image.open(self.folderSave+self.strSave)
        return plotImage
    def stripPlot(self):
        ### this makes the striplots
        ### if there is only one X group, make a simple stripplot without any hue (or secondary indepedent variable)
        if self.x1Group and not self.x2Group:
            plt.figure()
            ax1 = sns.stripplot(x=self.x1Group, y=self.yGroup,  ### putting the stipplot on that figure
                            jitter = 0.35,
                            size = 4,
                            #hue_order=clarity_ranking,
                            data=self.df)
            # self.ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            ax1.set_xticklabels(ax1.get_xticklabels(), rotation=30, ha="right")  ### rotating the axis labels so they don't bump into each other
            self.strSave = "striplPlot" + self.yGroup + self.title1Group + ".png" ## saving the plot
                    ########## sizing plot, adjusting bottom margin for long axis labels
            sns.set(rc={'figure.figsize':(self.sizeX,self.sizeY)}) ### setting figure size
            plt.subplots_adjust(bottom=0.2)
            plt.subplots_adjust(right=0.8)
            ########3
            titleSave = self.yGroup + " as a function of " + self.x1Group  ### saving the plot
            ax1.set_title(titleSave)
        ##### if there are two X groups then the "hue" is added to the striplot. the "palette" variable controls the color scheme for X2Group
        elif self.x1Group and self.x2Group:
            figure = plt.figure()
            ax1 = sns.stripplot(x=self.x1Group, y=self.yGroup,
                            hue=self.x2Group,
                            palette="bright",
                            jitter = 0.35,
                            size = 4,
                            #hue_order=clarity_ranking,
                            data=self.df)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
            ax1.set_xticklabels(ax1.get_xticklabels(), rotation=30, ha="right")
            self.strSave = "stripPlot" + self.yGroup + self.title1Group + self.title2Group + ".png"
                    ########## sizing plot, adjusting bottom margin for long axis labels
            sns.set(rc={'figure.figsize':(self.sizeX,self.sizeY)}) ######
            plt.subplots_adjust(bottom=0.2)
            plt.subplots_adjust(right=0.8)
            # ########3
            titleSave = self.yGroup + " as a function of " + self.x1Group + " and " + self.x2Group
            ax1.set_title(titleSave)
        # self.figure.tight_layout(pad = 0.5)
        plt.tight_layout()
        plt.savefig(self.folderSave + self.strSave)  # change to seaborn
        # plt.close()
        plotImage = PIL.Image.open(self.folderSave+self.strSave)
        return plotImage
    
    def pairPlot(self):
        #### creates a pairplot
        self.titleGroup = self.title1Group
        sns.set(font_scale=self.fntSz)
        if self.x1Group:
            plt.figure()
            sns.pairplot(self.df, vars = ['PCE', 'Voc', 'Jsc','FF'], hue = self.x1Group)
            self.strSave = 'pairPlot' + self.titleGroup + '.png'
            plt.savefig(self.folderSave+self.strSave)
           # plt.close()
        elif not self.x1Group:
            plt.figure()
            sns.pairplot(self.df, vars = ['PCE', 'Voc', 'Jsc','FF'])
            self.strSave = 'pairPlot_allDevices.png'
            plt.savefig(self.folderSave + self.strSave)
          #  plt.close()
            plt.plot_kws={"s": 0.1}#### adjusting the size of data points
        plt.tight_layout()
        plotImage = PIL.Image.open(self.folderSave+self.strSave)
        return plotImage
    

    
    
            