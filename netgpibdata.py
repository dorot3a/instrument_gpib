#! /usr/bin/env python
"""getgpibdata.py [-f filename] [-d devicename] [-i ip_address] [-a gpib_address] [--title Title] [--memo Memo]

 This script will get data from various GPIB devices through network and save the data into a data file.
 The name of the data file can be specified by '-f' option. If '-f myfile' is specified, 
 myfile.txt is the name of the data file. Also myfile.par will be created.
 The format of myfile.txt should be explained in myfile.txt along with various measurement
 parameters.
 Yoichi Aso  Sep 22 2008
 
 Updated Dorotea Macri 20260310"""

 

import re
import sys
import math
import optparse
import SR785
#import AG4395A
import netgpib
import datetime as dt
import os

#Usage text
usage = """usage: %prog [options]

This command will retrieve data from a network connected GPIB device.
The downloaded data will be saved to FILENAME.txt and the measurement parameters will be saved to FILENAME_params.txt.
Optionally, you can plot the downloaded data by specifying --plot option.
You need matplotlib and numpy modules to plot the data.
"""

#Parse options
sourcedir = os.path.expanduser("~") + '\\MIT Dropbox\\Dorotea Macri\\GRAVITES Measurements\\electronics testing\\'
parser = optparse.OptionParser(usage=usage)
parser.add_option("-f", "--file", dest="filename",
                  help="Output file name without an extension", default="data")
parser.add_option("-l", "--location", dest="folder",
                  help="Output location", default=sourcedir)
#by default saves to current directory
parser.add_option("-d", "--device",
                  dest="deviceName", default="SR785",
                  help="A GPIB device name. Default = SR785.")
parser.add_option("-a", "--address",
                  dest="gpibAddress", type="int", default=10,
                  help="GPIB device address")
parser.add_option("-i", "--ip",
                  dest="ipAddress", default="192.168.1.108",
                  help="IP address/Host name")
parser.add_option("--plot",
                  dest="plotData", default=False,
                  action="store_true",
                  help="Plot the downloaded data.")
parser.add_option("--xlin",
                  dest="xlog", default=True,
                  action="store_false",
                  help="Plot with linear x axis")
parser.add_option("--ylin",
                  dest="ylog", default=None,
                  action="store_false",
                  help="Plot with linear y axis")
parser.add_option("--xlog",
                  dest="xlog", default=True,
                  action="store_true",
                  help="Plot with logarithmic x axis")
parser.add_option("--ylog",
                  dest="ylog", default=None,
                  action="store_true",
                  help="Plot with logarithmic y axis")
parser.add_option("--title",
                  dest="title", type="string",default="",
                  help="Title of the measurement. The given string will be written into the parameter file.")
parser.add_option("--memo",
                  dest="memo", type="string",default="",
                  help="Use this option to note miscellaneous things.")


(options, args) = parser.parse_args()

# # Open socket

print('Connecting to '+str(options.ipAddress))

#Create a netGPIB object
gpibObj = netgpib.netGPIB(options.ipAddress, options.gpibAddress, '\004',0)

print('done.')

#automatically add date/time to filename
d = dt.datetime.now().strftime('%Y-%m-%d_%H%M_')
# open files
dataFileName=d+options.filename+'.txt'
paramFileName=d+options.filename+'_param.txt'
file_path = options.folder 

dataFile = open(file_path+dataFileName,'w')
paramFile = open(file_path+paramFileName,'w')

print('Data will be written into '+dataFileName)
print('Parameters will be written into '+paramFileName+'\n')

#Deal with an empty title
if options.title == "":
    options.title = options.filename

#Write the title and the memo string into the parameter file
paramFile.write('Title: '+options.title+'\n')
paramFile.write('Memo: '+options.memo+'\n')

#Call suitable functions for getting data
if options.deviceName == 'SR785':
    SR785.getparam(gpibObj, options.filename, dataFile, paramFile)
    SR785.getdata(gpibObj, dataFile, paramFile)

    
    dataFile.close()
    paramFile.close()
    gpibObj.close()
    
    if options.plotData:
        import gpibplot
        gpibplot.plotSR785(options.filename,xlog=options.xlog,ylog=options.ylog)
        input('Press enter to quit:')
elif options.deviceName == 'AG4395A':
    AG4395A.getdata(gpibObj, dataFile, paramFile)
    AG4395A.getparam(gpibObj, options.filename, dataFile, paramFile)

    dataFile.close()
    paramFile.close()
    gpibObj.close()


