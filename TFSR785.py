#!/usr/bin/env python3
"""
TFSR785.py - Transfer function measurement using SR785 network analyzer

Command a SR785 to execute a transfer function measurement with various
configurable measurement conditions.

Yoichi Aso  Sep 22 2008
Updated 2026 by Dorotea Macri
"""

import argparse
import sys
import math
import time
import netgpib
import SR785
import termstatus
import os 
from datetime import datetime as dt

sourcedir = os.path.expanduser("~") + r'/MIT Dropbox/Dorotea Macri/GRAVITES Measurements/electronics testing/'

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute a transfer function measurement using SR785.\n"
                    "Measurement results are saved in FILENAME.dat and parameters in FILENAME.par.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument("-f", "--file", dest="filename", default="TF",
                        help="Output file name without extension (default: TF)")
    parser.add_argument("-l", "--location", dest="folder",
                        help="Output location", default=sourcedir)
    parser.add_argument("-i", "--ip", dest="ipAddress", default="192.168.1.108",
                        help="IP address/Host name (default: 192.168.1.108)")
    parser.add_argument("-a", "--address", dest="gpibAddress", type=int, default=10,
                        help="GPIB device address (default: 10)")
    parser.add_argument("-s", "--startfreq", dest="startFreq", default="100kHz",
                        help="Start frequency with units (mHz, Hz, kHz) (default: 100kHz)")
    parser.add_argument("-e", "--stopfreq", dest="stopFreq", default="10kHz",
                        help="Stop frequency with units (mHz, Hz, kHz) (default: 10kHz)")
    parser.add_argument("-n", "--numpoints", dest="numOfPoints", type=int, default=50,
                        help="Number of frequency points (default: 50)")
    parser.add_argument("--sweep", dest="sweepType", type=str, default="Log",
                        choices=["Log", "Linear"],
                        help="Sweep type: Log or Linear (default: Log)")
    parser.add_argument("-x", "--excamp", dest="excAmp", default="1mV",
                        help="Excitation amplitude (default: 1mV)")
    parser.add_argument("-c", "--settlecycle", dest="settleCycles", type=int, default=10,
                        help="Settle cycles (default: 10)")
    parser.add_argument("-t", "--intcycle", dest="intCycles", type=int, default=20,
                        help="Integration cycles (default: 20)")
    parser.add_argument("--ic1", dest="inputCoupling1", type=str, default="DC",
                        choices=["AC", "DC"],
                        help="CH1 input coupling: AC or DC (default: DC)")
    parser.add_argument("--ic2", dest="inputCoupling2", type=str, default="DC",
                        choices=["AC", "DC"],
                        help="CH2 input coupling: AC or DC (default: DC)")
    parser.add_argument("--ig1", dest="inputGND1", type=str, default="Float",
                        choices=["Float", "Ground"],
                        help="CH1 input grounding: Float or Ground (default: Float)")
    parser.add_argument("--ig2", dest="inputGND2", type=str, default="Float",
                        choices=["Float", "Ground"],
                        help="CH2 input grounding: Float or Ground (default: Float)")
    parser.add_argument("--armode", dest="arMode", type=str, default="UpOnly",
                        choices=["UpOnly", "Tracking"],
                        help="Auto range mode: UpOnly or Tracking (default: UpOnly)")
    parser.add_argument("--plot", dest="plotData", action="store_true",
                        help="Plot the downloaded data (requires matplotlib and numpy)")
    parser.add_argument("--title", dest="title", type=str, default="",
                        help="Title of the measurement for parameter file")
    parser.add_argument("--memo", dest="memo", type=str, default="",
                        help="Miscellaneous notes for the measurement")
    
    return parser.parse_args()



def setup_input_channels(gpib_obj, options):
    """Configure input channels."""
    # CH1 Input Coupling
    icp1 = "1" if options.inputCoupling1 == "AC" else "0"
    gpib_obj.command(f'I1CP{icp1}')
    time.sleep(0.1)
    
    # CH2 Input Coupling
    icp2 = "1" if options.inputCoupling2 == "AC" else "0"
    gpib_obj.command(f'I2CP{icp2}')
    time.sleep(0.1)
    
    # CH1 Input GND
    igd1 = "0" if options.inputGND1 == "Float" else "1"
    gpib_obj.command(f'I1GD{igd1}')
    time.sleep(0.1)
    
    # CH2 Input GND
    igd2 = "0" if options.inputGND2 == "Float" else "1"
    gpib_obj.command(f'I2GD{igd2}')
    time.sleep(0.1)
    
    # AutoRange Off
    gpib_obj.command('A1RG0')
    time.sleep(0.1)
    gpib_obj.command('A2RG0')
    time.sleep(0.1)
    
    # Auto Range Mode
    ar_mode_id = '1' if options.arMode == "Tracking" else '0'
    gpib_obj.command(f'I1AR{ar_mode_id}')
    time.sleep(0.1)
    gpib_obj.command(f'I2AR{ar_mode_id}')
    time.sleep(0.1)
    
    # AutoRange On
    gpib_obj.command('A1RG1')
    time.sleep(0.1)
    gpib_obj.command('A2RG1')
    time.sleep(0.1)
    
    # Anti-Aliasing filter On
    gpib_obj.command('I1AF1')
    time.sleep(0.1)
    gpib_obj.command('I2AF1')
    time.sleep(0.1)


def setup_measurement_parameters(gpib_obj, options):
    """Configure measurement parameters."""
    # Display setup
    gpib_obj.command('DFMT1')  # Dual display
    time.sleep(0.1)
    gpib_obj.command('ACTD0')  # Active display 0
    time.sleep(0.1)
    
    # Measurement setup
    gpib_obj.command('MGRP2,3')  # Measurement Group = Swept Sine
    time.sleep(0.1)
    gpib_obj.command('MEAS2,47')  # Frequency Response
    time.sleep(0.1)
    
    # Display 0 = LogMag
    gpib_obj.command('VIEW0,0')
    time.sleep(0.1)
    # Display 1 = Phase
    gpib_obj.command('VIEW1,5')
    time.sleep(0.1)
    
    # Units
    gpib_obj.command('UNDB0,1')  # dB ON
    time.sleep(0.1)
    gpib_obj.command('UNPK0,0')  # PK Unit Off
    time.sleep(0.1)
    gpib_obj.command('UNDB1,0')  # dB OFF
    time.sleep(0.1)
    gpib_obj.command('UNPK1,0')  # PK Unit Off
    time.sleep(0.1)
    gpib_obj.command('UNPH1,0')  # Phase Unit deg.
    time.sleep(0.1)
    
    # Live display
    gpib_obj.command('DISP0,1')
    time.sleep(0.1)
    gpib_obj.command('DISP1,1')
    time.sleep(0.1)
    
    # Measurement parameters
    gpib_obj.command(f'SSCY2,{options.settleCycles}')  # Settle cycles
    time.sleep(0.1)
    gpib_obj.command(f'SICY2,{options.intCycles}')  # Integration cycles
    time.sleep(0.1)
    gpib_obj.command(f'SSTR2,{options.startFreq}')  # Start frequency
    time.sleep(0.1)
    gpib_obj.command(f'SSTP2,{options.stopFreq}')  # Stop frequency
    time.sleep(0.1)
    gpib_obj.command(f'SNPS2,{options.numOfPoints}')  # Number of points
    time.sleep(0.1)
    gpib_obj.command('SRPT2,0')  # Single shot mode
    time.sleep(0.1)
    
    # Sweep type
    sweep_type_id = '0' if options.sweepType == 'Linear' else '1'
    gpib_obj.command(f'SSTY2,{sweep_type_id}')
    time.sleep(0.1)
    
    # Source amplitude
    gpib_obj.command(f'SSAM{options.excAmp}')
    time.sleep(0.1)


def wait_for_measurement(gpib_obj, num_points):
    """Wait for measurement to complete."""
    measuring = True
    percentage = 0
    progress_info = termstatus.statusTxt('0%')
    
    while measuring:
        # Get status
        measuring = not int(gpib_obj.query('DSPS?4'))
        accomplished = int(gpib_obj.query('SSFR?'))
        percentage = int(math.floor(100 * accomplished / num_points))
        progress_info.update(f'{percentage}%')
        time.sleep(0.3)
    
    progress_info.end('100%')


def download_data(gpib_obj):
    """Download measurement data from both displays."""
    data = []
    freq = None
    
    for disp in range(2):
        print(f'Downloading data from display #{disp}')
        (f, d) = SR785.downloadData(gpib_obj, disp)
        data.append(d)
        if freq is None:
            freq = f
    
    return freq, data


def write_data_file(filename, freq, data):
    """Write data to file."""
    print('Writing data into the data file ...')
    with open(filename, 'w') as data_file:
        for i in range(len(freq)):
            line = freq[i]
            for disp in range(len(data)):
                line += f' {data[disp][i]}'
            data_file.write(line + '\n')


def write_param_file(filename, options, gpib_obj):
    """Write measurement parameters to file."""
    print('Writing measurement parameters into the parameter file ...')
    
    title = options.title if options.title else options.filename
    
    with open(filename, 'w') as param_file:
        param_file.write('#SR785 Transfer function measurement\n')
        param_file.write('#Column format = [Freq  Mag(dB) Phase(deg) NormVar1  NormVar2]\n')
        param_file.write(f'Title: {title}\n')
        param_file.write(f'Memo: {options.memo}\n')
        param_file.write('#---------- Measurement Setup ------------\n')
        param_file.write(f'Start frequency = {options.startFreq}\n')
        param_file.write(f'Stop frequency = {options.stopFreq}\n')
        param_file.write(f'Number of frequency points = {options.numOfPoints}\n')
        param_file.write(f'Excitation amplitude = {options.excAmp}\n')
        param_file.write(f'Settling cycles = {options.settleCycles}\n')
        param_file.write(f'Integration cycles = {options.intCycles}\n')
        param_file.write('\n')
        
        # Append device parameters
        SR785.getparam(gpib_obj, options.filename, None, param_file)


def main():
    """Main program."""
    options = parse_args()
    fpath = options.folder
    
    # Connect to device
    print(f'Connecting to {options.ipAddress} ...', end=' ')
    sys.stdout.flush()
    gpib_obj = netgpib.netGPIB(options.ipAddress, options.gpibAddress, '\004', 0)
    print('done.')
    
    # File names
    timestamp = dt.now().strftime('%Y-%m-%d_%H%M_')
    data_filename = f'{timestamp}_{options.filename}.txt'
    param_filename = f'{data_filename}_param.txt'
    
    print(f'Data will be written into {data_filename}')
    print(f'Parameters will be written into {param_filename}')
    print('Setting up parameters for the measurement')
    
    try:
        # Set output to GPIB
        gpib_obj.command("OUTX0")
        time.sleep(0.1)
        
        # Setup input channels and measurement
        setup_input_channels(gpib_obj, options)
        setup_measurement_parameters(gpib_obj, options)
        
        # Start measurement
        print('Transfer function measurement started:', end=' ')
        sys.stdout.flush()
        num_points = int(gpib_obj.query('SNPS?0'))
        time.sleep(0.1)
        gpib_obj.command('STRT')
        time.sleep(0.5)
        
        # Wait for measurement to complete
        wait_for_measurement(gpib_obj, num_points)
        
        # Download data
        time.sleep(2)
        freq, data = download_data(gpib_obj)
        
        # Write files
        write_data_file(fpath + data_filename, freq, data)
        write_param_file(fpath + param_filename, options, gpib_obj)
        
        print('Measurement completed successfully.')
        
        # Plot if requested
        if options.plotData:
            try:
                import plotgpibdata
                plotgpibdata.plotTFSR785(options.filename)
                input('Press enter to quit: ')
            except ImportError:
                print("Warning: matplotlib and/or numpy not available. Skipping plot.")
    
    finally:
        gpib_obj.close()


if __name__ == '__main__':
    main()