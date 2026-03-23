# -*- coding: utf-8 -*-
"""
Created on Wed Mar 18 18:07:29 2026

@author: tea
"""

import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
import os  
import argparse
from pathlib import Path
import re
import fileinput
import csv

sourcedir = os.path.expanduser("~") + '\\MIT Dropbox\\Dorotea Macri\\GRAVITES Measurements\\'

#Usage text
usage="""usage: %prog [options] Unzip measurements taken simultaneously on the SR785 to produce two sets of measurement files,
 as if the measurements were taken individually"""
 
def unzip_files(filename, filedir, save1, save2):
    print('!')
    print(filename)
    pattern = re.compile(re.escape(filename))  # escape special regex chars
    parampat = re.compile('_param')
    print(filedir)

    fpath = None
    paramFile = None

    for f in filedir.rglob('*'):
        if f.is_file() and pattern.search(f.name):  # ✅ Search f.name, not filename
            print(f)
            if parampat.search(f.name):
                paramFile = f
            else:
                fpath = f

    # Check if both files were found
    if fpath is None:
        raise FileNotFoundError(f"Data file not found matching: {filename}")
        if paramFile is None:
            raise FileNotFoundError(f"Parameter file not found for: {filename}")

        
    #get header of file
    with open(fpath, newline='') as f:
         reader = csv.reader(f)
         header = str(next(reader)[0])       
    print(header)
    #read in double file 
    data = pd.read_csv(fpath, comment='#', sep=',', header=None, 
                       names=['freq', 'display0', 'display1'])
    
    #open and copy params file         
    with open(paramFile, 'r') as f:
        content = f.read()
        
    data1 = data.copy()
    data1.drop('display1', axis=1, inplace=True)
    
    data2 = data.copy()
    data2.drop('display0', axis=1, inplace=True)
    
    output_files = [[save1, data1], [save2, data2]]
    
    for files in output_files:
        fname = files[0] + '.txt'
        paramname = files[0] + '_param.txt'
    
        # ✅ Use Path's / operator instead of string concatenation
        filesavepath = filedir / fname
        paramsavepath = filedir / paramname
        df = files[1]
    
        second_col = df.columns[1]
    
        # ✅ Add debugging to see actual paths
        print(f"Writing to: {filesavepath}")
        print(f"Path exists: {filesavepath.parent.exists()}")
    
        try:
            with open(filesavepath, 'w') as f:
                f.write(header + '\n')
                for _, row in df.iterrows():
                    f.write(f'{row["freq"]:+.7e}, {row[second_col]:+.7e}\n')
        
            print(f"✓ Created {fname}")
        except Exception as e:
            print(f"✗ Error writing {fname}: {e}")
    
        try:
            with open(paramsavepath, 'w') as f:
                f.write(content)
                print(f"✓ Created {paramname}")
        except Exception as e:
            print(f"✗ Error writing {paramname}: {e}")
            
    print('done!')

    return 
             
parser = argparse.ArgumentParser(description="Unzip 2-display SR785 Measurements")
parser.add_argument("-d", "--directory", dest="directory",
                    help="base directory to look in", default=sourcedir,
                    nargs='+')
parser.add_argument("-f", "--filename", dest="fname",
                    help="file name or partial name; use * to leave gaps", default="*")
parser.add_argument("-s1", "--savename1", dest="savename1",
                  help="Save the first output file as...", default='data_1')
parser.add_argument("-s2", "--savename2", dest="savename2",
                  help="Save the first output file as...", default='data_2')

args = parser.parse_args()

sourcedir = Path(args.directory)
sourcepath = Path(sourcedir)

filename = args.fname

unzip_files(filename, sourcedir, args.savename1, args.savename2)
