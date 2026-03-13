#!/usr/bin/env python
"""A quick way to plot data downloaded by netgpibdata.py"""
import argparse
from pathlib import Path
import gpibplot

# Usage text
usage = """
Plot the data downloaded by netgpibdata.py.
Data is read from FILENAME.txt and the associated parameters are read from FILENAME.par.
You can start an ipython session after a plot is generated. This enables one to change annotations/appearance of the plot.
"""

# Parse options
parser = argparse.ArgumentParser(description=usage)
parser.add_argument("-f", "--file", dest="filename",
                    help="Filename without an extension from which the data and parameters are read.",
                    default="data")
parser.add_argument("-l", "--location", dest="folder",
                    help="Output location",
                    nargs='+',
                    default=["C:/Users/tea/MIT Dropbox/Dorotea Macri/GRAVITES Measurements/electronics testing/"])
parser.add_argument("-i", "--ipython",
                    dest="ipython", default=False,
                    action="store_true",
                    help="Invoke ipython to interactively change the plot")

# Axis scale options
xaxis = parser.add_mutually_exclusive_group()
xaxis.add_argument("--xlin", dest="xlog",
                   action="store_false",
                   help="Plot with linear x axis")
xaxis.add_argument("--xlog", dest="xlog",
                   action="store_true", default=True,
                   help="Plot with logarithmic x axis (default)")

yaxis = parser.add_mutually_exclusive_group()
yaxis.add_argument("--ylin", dest="ylog",
                   action="store_false",
                   help="Plot with linear y axis")
yaxis.add_argument("--ylog", dest="ylog",
                   action="store_true", default=None,
                   help="Plot with logarithmic y axis")

args = parser.parse_args()

# Rejoin folder path in case spaces caused it to split
folder = Path(" ".join(args.folder))
fpath = folder / args.filename

ax = gpibplot.plotSR785(fpath, xlog=args.xlog, ylog=args.ylog)
fig = ax[0].figure

if args.ipython:
    from IPython import embed
    embed(header="""The following objects are exported:
    ax: a list of axes objects.
    fig: figure object.""")
else:
    input("Press enter to quit: ")
