from numpy import array, transpose, hstack
import fileinput
import matplotlib.pyplot as mpl
import re

def plotSR785(filename, xlog=True, ylog=None):
    """Plot downloaded data from SR785 """
    dataFile = filename + '.txt'
    paramFile = filename + '_params.txt'

    # Scan parameter file to get units
    unitLinePat = re.compile(r'^Unit:')
    measLinePat = re.compile(r'^Measurements:')
    mgLinePat = re.compile(r'^Measurement Group:')
    quotePat = re.compile(r'"([^"]*)"')
    units = []
    titles = []
    dataType = 'other'

    for line in fileinput.input(paramFile):
        if unitLinePat.match(line):
            units = quotePat.findall(line)
            for i in range(len(units)):
                units[i] = re.sub(r'rt', r'$\\mathsf{\\sqrt{\1}}$', units[i])
        if measLinePat.match(line):
            titles = quotePat.findall(line)
        if mgLinePat.match(line):
            mgs = quotePat.findall(line)
            if mgs[0] == 'FFT':
                dataType = 'spectrum'
            else:
                dataType = 'other'
    fileinput.close()

    # Read data
    firstLine = True
    dispLinePat = re.compile(r'^#Display')
    dispID = -1
    data = []

    if dataType == 'spectrum':
        for line in fileinput.input(dataFile):
            if dispLinePat.match(line):
                firstLine = True
                dispID += 1
                continue
            if line.strip()[0] == '#':
                continue
            if firstLine:
                data.append(transpose(array([list(map(float, line.split()))])))
                firstLine = False
            else:
                data[dispID] = hstack((data[dispID], transpose(array([list(map(float, line.split()))]))))
        fileinput.close()

        # Plot spectra
        numPlot = len(data)
        fig = mpl.figure()
        fig.subplots_adjust(hspace=0.4)
        axList = []
        for i in range(numPlot):
            axList.append(fig.add_subplot(numPlot, 1, i + 1))
            axList[i].plot(data[i][0], data[i][1])
            if (data[i][1].min() > 0) and ((ylog is None) or (ylog is True)):
                axList[i].set_yscale('log')
            if xlog:
                axList[i].set_xscale('log')
            axList[i].grid(True)
            axList[i].set_xlabel('Frequency [Hz]')
            axList[i].set_ylabel(units[i])
            axList[i].set_title(titles[i])
            axList[i].autoscale_view(True, True, False)

    else:  # Not spectrum data
        for line in fileinput.input(dataFile):
            if line.strip()[0] == '#':
                continue
            if firstLine:
                data = transpose(array([list(map(float, line.split()))]))
                firstLine = False
            else:
                data = hstack((data, transpose(array([list(map(float, line.split()))]))))
        fileinput.close()

        # Plot non-spectrum data
        numPlot = len(data) - 1
        fig = mpl.figure()
        fig.subplots_adjust(hspace=0.4)
        axList = []
        for i in range(numPlot):
            axList.append(fig.add_subplot(numPlot, 1, i + 1))
            axList[i].plot(data[0], data[i + 1])
            if (data[i + 1].min() > 0) and (ylog is True):
                axList[i].set_yscale('log')
            if xlog:
                axList[i].set_xscale('log')
            axList[i].grid(True)
            axList[i].set_xlabel('Frequency [Hz]')
            axList[i].set_ylabel(units[i])
            axList[i].set_title(titles[i])
            axList[i].autoscale_view(True, True, False)
        plot_title = input('Enter plot title:')
        fig.suptitle(plot_title)
        
    fig.show()
    return axList


def plotTFSR785(filename):
    """Plot TF data from SR785 """
    dataFile = filename + '.txt'

    # Read data
    firstLine = True
    data = None
    for line in fileinput.input(dataFile):
        if line.strip()[0] == '#':
            continue
        if firstLine:
            data = transpose(array([list(map(float, line.split()))]))
            firstLine = False
        else:
            data = hstack((data, transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    fig = mpl.figure()
    axList = []

    mag = fig.add_subplot(3, 1, 1)
    mag.plot(data[0], data[1])
    mag.set_xscale('log')
    mag.grid(True)
    mag.set_ylabel('Mag [dB]')
    mag.set_title('Transfer function')
    mag.autoscale_view(True, True, False)

    phase = fig.add_subplot(3, 1, 2)
    phase.plot(data[0], data[2])
    phase.grid(True)
    phase.set_ylabel('Phase [deg]')
    phase.set_xscale('log')
    phase.autoscale_view(True, True, False)

    coh = fig.add_subplot(3, 1, 3)
    coh.plot(data[0], data[3], label='Norm Var 1')
    coh.plot(data[0], data[4], label='Norm Var 2')
    coh.grid(True)
    coh.set_xscale('log')
    coh.set_ylabel('Normalized Variance')
    coh.set_xlabel('Frequency [Hz]')
    coh.set_ylim(0, 1.03)
    coh.legend(loc=0)
    coh.autoscale_view(True, True, False)

    fig.show()
    return [mag, phase, coh]


def plotTSSR785(filename):
    """Plot TS data from SR785 """
    dataFile = filename + '.txt'

    # Read data
    firstLine = True
    timeSeries = True
    timeLinePat = re.compile(r'^#Time series')
    histLinePat = re.compile(r'^#Histogram')
    tDispID = -1
    hDispID = -1
    tsData = []
    hsData = []

    for line in fileinput.input(dataFile):
        if timeLinePat.match(line):
            firstLine = True
            timeSeries = True
            tDispID += 1
            continue
        if histLinePat.match(line):
            firstLine = True
            timeSeries = False
            hDispID += 1
            continue
        if line.strip()[0] == '#':
            continue
        if firstLine:
            if timeSeries:
                tsData.append(transpose(array([list(map(float, line.split()))])))
            else:
                hsData.append(transpose(array([list(map(float, line.split()))])))
            firstLine = False
        else:
            if timeSeries:
                tsData[tDispID] = hstack((tsData[tDispID], transpose(array([list(map(float, line.split()))]))))
            else:
                hsData[hDispID] = hstack((hsData[hDispID], transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    numFig = len(tsData) + len(hsData)
    half = numFig // 2  # Integer division fix for Python 3
    fig = mpl.figure()
    fig.subplots_adjust(hspace=0.4)
    axList = []

    for i in range(half):  # Plot time series
        axList.append(fig.add_subplot(half, half, i + 1))
        axList[i].plot(tsData[i][0], tsData[i][1])
        axList[i].grid(True)
        axList[i].set_title('Time Series ' + str(i + 1))
        axList[i].set_ylabel('V')
        axList[i].set_xlabel('sec')

    for i in range(half):  # Plot histogram
        j = i + half
        axList.append(fig.add_subplot(half, half, j + 1))
        axList[j].plot(hsData[i][0], hsData[i][1])
        axList[j].grid(True)
        axList[j].set_title('Histogram ' + str(i + 1))
        axList[j].set_ylabel('Counts')
        axList[j].set_xlabel('V')

    fig.suptitle('Time series and histograms')
    fig.show()
    return axList


def plotSPAG4395A(filename, title, xlog=True, ylog=True, psdunits=False):
    """Plot downloaded spectrum data from AG4395A """
    dataFile = filename + '.txt'

    firstLine = True
    data = None
    for line in fileinput.input(dataFile):
        if line.strip()[0] == '#':
            continue
        if firstLine:
            data = transpose(array([list(map(float, line.split()))]))
            firstLine = False
        else:
            data = hstack((data, transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    fig = mpl.figure()
    mag = fig.add_subplot(1, 1, 1)
    mag.plot(data[0], data[1])
    mag.set_yscale('log' if ylog else 'linear')
    mag.set_xscale('log' if xlog else 'linear')
    mag.grid(True)
    mag.set_ylabel('Vrms/rt(Hz)' if psdunits else 'Mag [dB]')
    mag.set_xlabel('Frequency [Hz]')
    mag.set_title(title)
    mag.autoscale_view(True)

    fig.show()
    return mag


def plotTFAG4395A(filename, title):
    """Plot TF data from AG4395A """
    dataFile = filename + '.txt'

    firstLine = True
    data = None
    for line in fileinput.input(dataFile):
        if line.strip()[0] == '#':
            continue
        if firstLine:
            data = transpose(array([list(map(float, line.split()))]))
            firstLine = False
        else:
            data = hstack((data, transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    fig = mpl.figure()
    mag = fig.add_subplot(2, 1, 1)
    mag.plot(data[0], data[1])
    mag.set_xscale('log')
    mag.grid(True)
    mag.set_ylabel('Mag [dB]')
    mag.set_title(title)
    mag.autoscale_view(True, True)

    phase = fig.add_subplot(2, 1, 2)
    phase.plot(data[0], data[2])
    phase.grid(True)
    phase.set_ylabel('Phase [deg]')
    phase.set_xscale('log')
    phase.autoscale_view(True, True)

    fig.show()
    return [mag, phase]


def plotTFHP4195A(filename, title):
    """Plot TF data from HP4195A """
    dataFile = filename + '.txt'

    firstLine = True
    data = None
    for line in fileinput.input(dataFile):
        if line.strip()[0] == '#':
            continue
        if firstLine:
            data = transpose(array([list(map(float, line.split()))]))
            firstLine = False
        else:
            data = hstack((data, transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    fig = mpl.figure()
    mag = fig.add_subplot(2, 1, 1)
    mag.plot(data[0], data[1])
    mag.set_xscale('log')
    mag.grid(True)
    mag.set_ylabel('Mag [dB]')
    mag.set_title(title)
    mag.autoscale_view(True, True)

    phase = fig.add_subplot(2, 1, 2)
    phase.plot(data[0], data[2])
    phase.grid(True)
    phase.set_ylabel('Phase [deg]')
    phase.set_xscale('log')
    phase.autoscale_view(True, True)

    fig.show()
    return [mag, phase]


def plotSPHP4195A(filename, title, xlog=True, ylog=True, psdunits=False):
    """Plot downloaded spectrum data from HP4195A """
    dataFile = filename + '.txt'

    firstLine = True
    data = None
    for line in fileinput.input(dataFile):
        if line.strip()[0] == '#':
            continue
        if firstLine:
            data = transpose(array([list(map(float, line.split()))]))
            firstLine = False
        else:
            data = hstack((data, transpose(array([list(map(float, line.split()))]))))
    fileinput.close()

    fig = mpl.figure()
    mag = fig.add_subplot(1, 1, 1)
    mag.plot(data[0], data[1])
    mag.set_yscale('log' if ylog else 'linear')
    mag.set_xscale('log' if xlog else 'linear')
    mag.grid(True)
    mag.set_ylabel('uV/rt(Hz)' if psdunits else 'Mag [dBm]')
    mag.set_xlabel('Frequency [Hz]')
    mag.set_title(title)
    mag.autoscale_view(True)

    fig.show()
    return mag
