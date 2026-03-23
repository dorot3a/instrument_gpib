# -*- coding: utf-8 -*-
"""
Created on Wed Dec  6 13:15:59 2023

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

sourcedir = os.path.expanduser("~") + '\\MIT Dropbox\\Dorotea Macri\\GRAVITES Measurements\\'

#Usage text
usage="""usage: %prog [options]
Stitch a number of frequency spans from a sr785 measurement together, retaining the highest resolution measurements from each file
"""
parser = argparse.ArgumentParser(description="Stitch frequency spans together")
parser.add_argument("-d", "--directory", dest="directory",
                    help="base directory to look in", default=sourcedir,
                    nargs='+')
parser.add_argument("-f", "--filename", dest="fname",
                    help="file name or partial name; use * to leave gaps", default="*")
parser.add_argument("-s", "--savename", dest="savename",
                  help="Save the output file as...", default='combined_data')
args = parser.parse_args()

sourcedir = Path(args.directory)
sourcepath = Path(sourcedir)

print("searching " + str(sourcedir))

pattern = re.compile(args.fname)
parampat = re.compile('param')
fspanlinepat = re.compile('Frequency Span')

file_paths = []
file_names = []
fspan = []

for f in sourcepath.rglob('*'):
    if f.is_file() and pattern.search(f.name):
        if parampat.search(f.name):
            #skip the parameter files 
            pass
        else:
            #print(f.name[0:-4])
            #find the parameter file
            pat2 = re.compile(f.name[0:-4] + "_param")
            paramFile = [f for f in sourcepath.rglob('*') if f.is_file() and pat2.search(str(f))][0]
            #print(paramFile)
            for line in fileinput.input(str(paramFile)):
                if fspanlinepat.search(line):
                    match = re.search(r'[\d.]+', line)
                    span = float(match.group()) if match else None
                    #print(span)
                    file_paths.append(f)
                    file_names.append(f.name)
                    fspan.append(span)
                    
df = pd.DataFrame({'file': file_paths, 'name': file_names, 'span': fspan})
df = df.sort_values(by='span', key=abs, ascending=True)
#print(file_names)
print(df)

combined = None

for fname in df['file']:
    data = pd.read_csv(fname, comment='#', sep=',', header=None, 
                       names=['freq', 'display0', 'display1'])
    
    # strip whitespace from values caused by the comma+space separator
    data = data.apply(lambda col: pd.to_numeric(col.astype(str).str.strip(), errors='coerce'))

    if combined is None:
        combined = data
    else:
        new_data = data[~data['freq'].isin(combined['freq'])]
        combined = pd.concat([combined, new_data], ignore_index=True)

combined = combined.sort_values('freq').reset_index(drop=True)
file_dir = Path(df['file'].iloc[0]).parent
savepath = Path(str(file_dir) + '\\' + args.savename)

with open(savepath, 'w') as f:
    f.write('# Combined data file\n')
    for _, row in combined.iterrows():
        f.write(f'{row["freq"]:+.7e}, {row["display0"]:+.7e}, {row["display1"]:+.7e}\n')

#write a dummy param file to plot nicely 
with open(paramFile, 'r') as f:
    content = f.read()
with open(Path(str(savepath) + '_params'), 'w') as f:
    f.write(content)
    
print(f"Output file: {savepath}")

print('done!')
# Frequency Resolution: 
# sort df by increasing bw

# make new df 

# for each pair read in 2 dfs 

#full_span = s
#concatenate 

# =============================================================================
# 
# 
# df_1.columns = ['Hz', 'V']
# df_2.columns = ['Hz', 'V']
# df_3.columns = ['Hz', 'V']
# df_4.columns = ['Hz', 'V']
# df_5.columns = ['Hz', 'V']
# df_6.columns = ['Hz', 'V']
# 
# 
# full_span = pd.concat([df_1, df_2[df_2['Hz'] > df_1['Hz'].iat[-1]], 
#                       df_3[df_3['Hz'] > df_2['Hz'].iat[-1]], 
#                       df_4[df_4['Hz'] > df_3['Hz'].iat[-1]], 
#                       df_5[df_5['Hz'] > df_4['Hz'].iat[-1]], 
#                       df_6[df_6['Hz'] > df_5['Hz'].iat[-1]]],
#                       ignore_index=True)
# 
# full_span.to_csv(savepath)
# 
# =============================================================================
