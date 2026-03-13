#! /usr/bin/env python3
#
# SPSR785.py [-f filename] [-i ip_address] [-a gpib_address] [{-b|--bandwidth} bw1 [bw2 ...]]
#                 [{-n|--numpoints} num_of_points] [{-v|--averaging} num_of_avg] [--avgmode avg_mode]
#                 [{-d|--dualchannel}] [--ic1 ch1_input_coupling] [--ic2 ch2_input_coupling]
#                 [--ig1 ch1_input_ground] [--ig2 ch2_input_ground] [{-w|--window} window_func]
#                 [--title Title] [--memo Memo]
#
# Command an SR785 to measure spectra. Multiple bandwidths can be provided to
# --bandwidth; the instrument will run one sequential measurement per bandwidth
# and save each result to a separate file.
#
# Yoichi Aso  Feb. 8 2009
# Updated Dorotea Macri 20260310
# Python 3 compatibility + multi-bandwidth support

import re
import sys
import math
import argparse
import time
import netgpib
import SR785
import termstatus
from datetime import datetime as dt

# ---------------------------------------------------------------------------
# Parse options
# ---------------------------------------------------------------------------
usage = """
This program remotely executes a spectrum measurement using SR785.
Various measurement conditions can be set using options.
The measurement result will be saved in FILENAME.txt and the measurement
parameters in FILENAME_params.txt.

Multiple bandwidths may be passed to --bandwidth; one sequential measurement
is taken per bandwidth, each saved to its own file.

Optionally, it can plot the retrieved data. You need matplotlib and numpy
modules to plot the data.
"""

parser = argparse.ArgumentParser(description=usage)
parser.add_argument("-f", "--file", dest="filename",
                    help="Output file name without an extension", default="data")
parser.add_argument("-l", "--location", dest="folder",
                    help="Output location",
                    default="C:/Users/ligo/MIT Dropbox/Dorotea Macri/GRAVITES Measurements/electronics testing/")
parser.add_argument("-i", "--ip",
                    dest="ipAddress", default="192.168.1.108",
                    help="IP address/Host name")
parser.add_argument("-a", "--address",
                    dest="gpibAddress", type=int, default=10,
                    help="GPIB device address")
parser.add_argument("-b", "--bandwidth",
                    dest="bandWidths", nargs='+', default=["102.4kHz"],
                    help="Bandwidth(s). Accepts one or more values with mHz, Hz or kHz units. "
                         "If multiple values are given, a separate measurement is taken for each.")
parser.add_argument("-n", "--numpoints",
                    dest="numOfPoints", type=int, default=800,
                    help="Number of frequency points")
parser.add_argument("-v", "--averaging",
                    dest="numAvg", type=int, default=100,
                    help="Number of averages")
parser.add_argument("--avgmode",
                    dest="avgMode", type=str, default="RMS",
                    help="Averaging mode: None, Vector, RMS or PeakHold")
parser.add_argument("-d", "--dualchannel", action="store_true",
                    dest="dual",
                    help="Set to the dual channel mode.")
parser.add_argument("--ic1",
                    dest="inputCoupling1", type=str, default="DC",
                    help="CH1 input coupling. DC or AC")
parser.add_argument("--ic2",
                    dest="inputCoupling2", type=str, default="DC",
                    help="CH2 input coupling. DC or AC")
parser.add_argument("--ig1",
                    dest="inputGND1", type=str, default="Float",
                    help="CH1 input grounding. Float or Ground")
parser.add_argument("--ig2",
                    dest="inputGND2", type=str, default="Float",
                    help="CH2 input grounding. Float or Ground")
parser.add_argument("-w", "--window",
                    dest="windowFunc", type=str, default="Hanning",
                    help="Window function: Uniform, Flattop, Hanning, BMH, Kaiser, "
                         "Force/Exponential, User, [-T/2,T/2], [0,T/2] or [-T/4,T/4]")
parser.add_argument("-o",
                    dest="order", default=False, action="store_true",
                    help="Channel assignment order: inverts order of window assignment "
                         "to CH2->displayA CH1->displayB")
parser.add_argument("--base",
                    dest="freqbase", type=float, default=102.4,
                    help="Frequency base: Set to 100 or 102.4 for 100kHz or 102.4kHz respectively")
parser.add_argument("--plot",
                    dest="plotData", default=False, action="store_true",
                    help="Plot the downloaded data.")
parser.add_argument("--xlin",
                    dest="xlog", default=True, action="store_false",
                    help="Plot with linear x axis")
parser.add_argument("--ylin",
                    dest="ylog", default=None, action="store_false",
                    help="Plot with linear y axis")
parser.add_argument("--xlog",
                    dest="xlog", default=True, action="store_true",
                    help="Plot with logarithmic x axis")
parser.add_argument("--ylog",
                    dest="ylog", default=None, action="store_true",
                    help="Plot with logarithmic y axis")
parser.add_argument("--title",
                    dest="title", type=str, default="",
                    help="Title of the measurement. Written into the parameter file.")
parser.add_argument("--memo",
                    dest="memo", type=str, default="",
                    help="Use this option to note miscellaneous things.")

options = parser.parse_args()

# ---------------------------------------------------------------------------
# Derived settings that are independent of bandwidth
# ---------------------------------------------------------------------------

# Convert number of points into available resolution
if options.numOfPoints <= 100:
    fRes = 0   # Resolution is 100 points
elif options.numOfPoints <= 200:
    fRes = 1   # Resolution is 200 points
elif options.numOfPoints <= 400:
    fRes = 2   # Resolution is 400 points
else:
    fRes = 3   # Resolution is 800 points

# Pick frequency base
base = 1 if options.freqbase == 102.4 else 0

# ---------------------------------------------------------------------------
# Connect to instrument (once, shared across all bandwidth sweeps)
# ---------------------------------------------------------------------------
print(f'Connecting to {options.ipAddress} ...')
gpibObj = netgpib.netGPIB(options.ipAddress, options.gpibAddress, '\004', 0)
print('done.')

# Set output to GPIB
gpibObj.command("OUTX0")
time.sleep(0.1)

# ---------------------------------------------------------------------------
# Input and common instrument setup (done once; independent of bandwidth)
# ---------------------------------------------------------------------------
print('Setting up parameters for the measurement')

# Input coupling
icp1 = "1" if options.inputCoupling1 == "AC" else "0"
gpibObj.command(f'I1CP{icp1}')   # CH1 Input Coupling
time.sleep(0.1)

icp2 = "1" if options.inputCoupling2 == "AC" else "0"
gpibObj.command(f'I2CP{icp2}')   # CH2 Input Coupling
time.sleep(0.1)

# Input grounding
igd1 = "0" if options.inputGND1 == "Float" else "1"
gpibObj.command(f'I1GD{igd1}')   # CH1 Input GND
time.sleep(0.1)

igd2 = "0" if options.inputGND2 == "Float" else "1"
gpibObj.command(f'I2GD{igd2}')   # CH2 Input GND
time.sleep(0.1)

# Auto-range
gpibObj.command('A1RG0')   # AutoRange Off
time.sleep(0.1)
gpibObj.command('A2RG0')   # AutoRange Off
time.sleep(0.1)
gpibObj.command('I1AR0')   # AutoRange Up Only
time.sleep(0.1)
gpibObj.command('I2AR0')   # AutoRange Up Only
time.sleep(0.1)
gpibObj.command('A1RG1')   # AutoRange On
time.sleep(0.1)
gpibObj.command('A2RG1')   # AutoRange On
time.sleep(0.1)

# Anti-aliasing filters
gpibObj.command('I1AF1')   # Anti-Aliasing filter On
time.sleep(0.1)
gpibObj.command('I2AF1')   # Anti-Aliasing filter On
time.sleep(0.1)

# Measurement group and input source
gpibObj.command('MGRP2,0')   # Measurement Group = FFT
time.sleep(0.1)
gpibObj.command('PAUS')      # Pause to stop data acquisition
time.sleep(0.1)
gpibObj.command('ISRC0')     # Input = Analog
time.sleep(0.1)
gpibObj.command(f'FBAS2,{base}')   # Base Frequency
time.sleep(0.1)

# Channel assignment order
if options.order:
    gpibObj.command('ACTD0')
    time.sleep(0.1)
    gpibObj.command('MEAS0,1')   # Display 0 = CH2
    time.sleep(0.1)
    gpibObj.command('ACTD1')
    time.sleep(0.1)
    gpibObj.command('MEAS1,0')   # Display 1 = CH1
    time.sleep(0.1)
else:
    gpibObj.command('ACTD0')
    time.sleep(0.1)
    gpibObj.command('MEAS0,0')   # Display 0 = CH1
    time.sleep(0.1)
    gpibObj.command('ACTD1')
    time.sleep(0.1)
    gpibObj.command('MEAS1,1')   # Display 1 = CH2
    time.sleep(0.1)

# Display format (single or dual)
if options.dual:
    gpibObj.command('DFMT1')   # Dual display
    time.sleep(0.1)
    numDisp = 2
else:
    gpibObj.command('DFMT0')   # Single display
    time.sleep(0.1)
    numDisp = 1

# Per-display view setup
for disp in range(numDisp):
    gpibObj.command(f'ACTD{disp}')      # Change active display
    time.sleep(0.1)
    gpibObj.command(f'VIEW{disp},0')    # Log Magnitude
    time.sleep(0.1)
    gpibObj.command(f'UNDB{disp},0')    # dB OFF
    time.sleep(0.1)
    gpibObj.command(f'UNPK{disp},2')    # Vrms
    time.sleep(0.1)
    gpibObj.command(f'PSDU{disp},1')    # PSD ON
    time.sleep(0.1)
    gpibObj.command(f'DISP{disp},1')    # Live display on
    time.sleep(0.1)

# Frequency resolution
gpibObj.command(f'FLIN2,{fRes}')   # Frequency resolution
time.sleep(0.1)

# Averaging settings
gpibObj.command('FAVG2,1')   # Averaging On
time.sleep(0.1)

avgModDict = {"None": 0, "Vector": 1, "RMS": 2, "PeakHold": 3}
avgModID = avgModDict.get(options.avgMode, 2)
gpibObj.command(f'FAVM2,{avgModID}')   # Averaging mode
time.sleep(0.1)

gpibObj.command('FAVT2,0')   # Averaging Type = Linear
time.sleep(0.1)
gpibObj.command('FREJ2,1')   # Overload Reject On
time.sleep(0.1)
gpibObj.command(f'FAVN2,{options.numAvg}')   # Number of averages
time.sleep(0.1)

# Window function
winFuncDict = {"Uniform": 0, "Flattop": 1, "Hanning": 2, "BMH": 3, "Kaiser": 4,
               "Force/Exponential": 5, "User": 6, "[-T/2,T/2]": 7,
               "[0,T/2]": 8, "[-T/4,T/4]": 9}
winFuncID = winFuncDict.get(options.windowFunc, 2)
gpibObj.command(f'FWIN2,{winFuncID}')   # Window function
time.sleep(0.1)

# ---------------------------------------------------------------------------
# Per-bandwidth measurement loop
# ---------------------------------------------------------------------------
saved_files = []   # collect base filenames for optional plotting

for bandWidth in options.bandWidths:

    print(f'\n--- Starting measurement for bandwidth: {bandWidth} ---')

    # Set bandwidth for this sweep
    gpibObj.command(f'FSPN2,{bandWidth}')   # Frequency span
    time.sleep(0.5)

    # Build filenames: embed bandwidth tag so files don't collide
    timestamp = dt.now().strftime('%Y-%m-%d_%H%M_')
    bw_tag = re.sub(r'[^\w.\-]', '_', bandWidth)   # sanitise for filesystem
    base_name = f'{timestamp}{options.filename}_{bw_tag}'
    dataFileName  = base_name + '.txt'
    paramFileName = base_name + '_params.txt'

    print(f'Data will be written into        {dataFileName}')
    print(f'Parameters will be written into  {paramFileName}')

    # Start measurement
    gpibObj.command('ACTD0')
    time.sleep(0.1)
    print('Measurement started')
    sys.stdout.flush()
    gpibObj.command('STRT')   # Start measurement
    time.sleep(0.1)

    # Wait for measurement to finish
    measuring = True
    print('Averaging completed: ', end='')
    avgStatus = termstatus.statusTxt("0")
    while measuring:
        response = gpibObj.query('DSPS?1').strip()
        measuring = not int(response)
        avg = int(gpibObj.query("NAVG?0"))
        avgStatus.update(str(avg))
        time.sleep(0.3)

    a = int(gpibObj.query("NAVG?0"))
    avgStatus.end(str(a))
    print('done')

    gpibObj.command('ASCL0')   # Auto scale
    gpibObj.command('ASCL1')   # Auto scale
    time.sleep(0.5)

    # Save data and parameters
    fpath = options.folder
    dataFile  = open(fpath + dataFileName,  'w')
    paramFile = open(fpath + paramFileName, 'w')

    SR785.getdata(gpibObj, dataFile, paramFile)

    # Write parameter block
    title = options.title if options.title else options.filename
    paramFile.write(f'Title: {title}\n')
    paramFile.write(f'Memo: {options.memo}\n')
    paramFile.write(f'Bandwidth: {bandWidth}\n')
    paramFile.write('############## Spectra measurement parameters #########################\n')

    fSpan = gpibObj.query("FSPN?0")[:-1]
    paramFile.write(f'Frequency Span: {fSpan}\n')

    fResVal = {0: 100, 1: 200, 2: 400, 3: 800}[int(gpibObj.query("FLIN?0"))]
    paramFile.write(f'Frequency Resolution: {fResVal}\n')

    nAvg = int(gpibObj.query("NAVG?0"))
    paramFile.write(f'Number of Averages: {nAvg}\n')

    avgModeStr = {0: "None", 1: "Vector", 2: "RMS", 3: "PeakHold"}[int(gpibObj.query("FAVM?0"))]
    paramFile.write(f'Averaging Mode: {avgModeStr}\n')

    winFuncStr = {0: "Uniform", 1: "Flattop", 2: "Hanning", 3: "BMH", 4: "Kaiser",
                  5: "Force/Exponential", 6: "User", 7: "[-T/2,T/2]",
                  8: "[0,T/2]", 9: "[-T/4,T/4]"}[int(gpibObj.query("FWIN?0"))]
    paramFile.write(f'Window function: {winFuncStr}\n')

    paramFile.write('####################################################################\n')

    SR785.getparam(gpibObj, options.filename, dataFile, paramFile)

    dataFile.close()
    paramFile.close()

    saved_files.append(fpath + base_name)
    print(f'Saved: {dataFileName}')

# ---------------------------------------------------------------------------
# Clean up
# ---------------------------------------------------------------------------
gpibObj.close()
print('\nAll measurements complete.')

# ---------------------------------------------------------------------------
# Optional plotting
# ---------------------------------------------------------------------------
if options.plotData:
    import gpibplot
    for fbase in saved_files:
        gpibplot.plotSR785(fbase, xlog=options.xlog, ylog=options.ylog)
    input('Press enter to quit: ')
