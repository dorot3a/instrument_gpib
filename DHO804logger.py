# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:55:20 2026

@author: tea
"""

import pyvisa
import csv
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

class RigolDHO804Logger:
    def __init__(self, visa_address=None, timeout=10000):
        """
        Initialize Rigol DHO804 oscilloscope connection via SCPI.
        
        Args:
            visa_address: VISA resource string
            timeout: Communication timeout in milliseconds
        """
        self.rm = pyvisa.ResourceManager()
        
        if visa_address is None:
            resources = self.rm.list_resources()
            print(f"Found devices: {resources}")
            if resources:
                visa_address = resources[0]
            else:
                raise ConnectionError("No oscilloscope found!")
        
        self.scope = self.rm.open_resource(visa_address)
        self.scope.timeout = timeout
        
        idn = self.scope.query("*IDN?")
        print(f"Connected to: {idn}")
    
    def get_waveform_data(self, channel=1):
        """Retrieve waveform data from specified channel (Rigol DHO804 specific)."""
        try:
            # Set data source
            self.scope.write(f":WAVeform:SOURce CH{channel}")
            time.sleep(0.2)
            
            # Get timebase scale
            time_div = float(self.scope.query(":TIMebase:MAIN:SCALe?"))
            time.sleep(0.1)
            
            # Get voltage scale
            volt_div = float(self.scope.query(f":CHANnel{channel}:SCALe?"))
            time.sleep(0.1)
            
            # Get sample rate
            sample_rate = float(self.scope.query(":WAVeform:SRATe?"))
            time.sleep(0.1)
            
            # Set waveform mode and format
            self.scope.write(":WAVeform:MODE RAW")
            time.sleep(0.1)
            self.scope.write(":WAVeform:FORMat ASCII")
            time.sleep(0.1)
            
            # Get record length
            record_length = int(self.scope.query(":WAVeform:POINts:MODE NORMal?") or 1000)
            time.sleep(0.1)
            
            # Get waveform data
            self.scope.write(":WAVeform:DATA?")
            time.sleep(0.3)
            raw_data = self.scope.read()
            
            # Parse data
            voltage_data = np.array([float(x) for x in raw_data.split(',')])
            time_data = np.arange(len(voltage_data)) / sample_rate
            
            metadata = {
                'channel': channel,
                'time_div': time_div,
                'volt_div': volt_div,
                'sample_rate': sample_rate,
                'record_length': len(voltage_data),
                'timestamp': datetime.now().isoformat()
            }
            
            return {'time': time_data, 'voltage': voltage_data, 'metadata': metadata}
        
        except Exception as e:
            print(f"Error reading CH{channel}: {e}")
            raise
    
    def get_channel_stats(self, channel=1):
        """Get measurement statistics for a channel."""
        try:
            # Enable measurements
            mean = float(self.scope.query(f":MEASure:STAT:MEAN? CH{channel}"))
            time.sleep(0.1)
            max_val = float(self.scope.query(f":MEASure:STAT:MAX? CH{channel}"))
            time.sleep(0.1)
            min_val = float(self.scope.query(f":MEASure:STAT:MIN? CH{channel}"))
            time.sleep(0.1)
            
            return {'mean': mean, 'max': max_val, 'min': min_val}
        except:
            return None
    
    def monitor_and_log(self, channels=[1, 2], interval=1.0, 
                        duration=None, filename='oscilloscope_data.csv'):
        """Continuously monitor channels and save to CSV."""
        csv_file = Path(filename)
        start_time = time.time()
        sample_count = 0
        
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = None
                
                while True:
                    elapsed = time.time() - start_time
                    if duration and elapsed > duration:
                        break
                    
                    row_data = {'timestamp': datetime.now().isoformat()}
                    
                    for ch in channels:
                        try:
                            stats = self.get_channel_stats(ch)
                            if stats:
                                row_data[f'CH{ch}_mean'] = stats['mean']
                                row_data[f'CH{ch}_min'] = stats['min']
                                row_data[f'CH{ch}_max'] = stats['max']
                        except Exception as e:
                            print(f"Error reading CH{ch}: {e}")
                    
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=row_data.keys())
                        writer.writeheader()
                    
                    writer.writerow(row_data)
                    sample_count += 1
                    
                    print(f"Sample {sample_count} recorded at {row_data['timestamp']}")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            print(f"\nLogging stopped. {sample_count} samples saved to {csv_file}")
        finally:
            self.close()
    
    def live_plot(self, channels=[1], duration=60, update_interval=1000):
        """Display live waveform plots from oscilloscope."""
        num_channels = len(channels)
        fig, axes = plt.subplots(num_channels, 1, figsize=(12, 4*num_channels))
        
        if num_channels == 1:
            axes = [axes]
        
        fig.suptitle('Rigol DHO804 Live Monitor', fontsize=14, fontweight='bold')
        
        lines = []
        data_buffers = {}
        start_time = time.time()
        
        for idx, ch in enumerate(channels):
            ax = axes[idx]
            line, = ax.plot([], [], lw=2, color=f'C{idx}')
            lines.append(line)
            data_buffers[ch] = {'time': deque(maxlen=5000), 'voltage': deque(maxlen=5000)}
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Voltage (V)')
            ax.set_title(f'Channel {ch}')
            ax.grid(True, alpha=0.3)
        
        def update_plot(frame):
            try:
                elapsed = time.time() - start_time
                if duration and elapsed > duration:
                    plt.close()
                    return lines
                
                for idx, ch in enumerate(channels):
                    waveform = self.get_waveform_data(ch)
                    time_data = waveform['time']
                    voltage_data = waveform['voltage']
                    
                    # Replace data instead of appending
                    data_buffers[ch]['time'] = deque(time_data, maxlen=5000)
                    data_buffers[ch]['voltage'] = deque(voltage_data, maxlen=5000)
                    
                    lines[idx].set_data(data_buffers[ch]['time'], data_buffers[ch]['voltage'])
                    
                    ax = axes[idx]
                    ax.relim()
                    ax.autoscale_view()
                    
                    if len(data_buffers[ch]['voltage']) > 0:
                        v_data = np.array(data_buffers[ch]['voltage'])
                        mean_v = np.mean(v_data)
                        max_v = np.max(v_data)
                        min_v = np.min(v_data)
                        ax.set_title(f'Channel {ch} | Mean: {mean_v:.3f}V | '
                                   f'Max: {max_v:.3f}V | Min: {min_v:.3f}V')
                
                return lines
            
            except Exception as e:
                print(f"Error in plot update: {e}")
                return lines
        
        ani = FuncAnimation(fig, update_plot, interval=update_interval, blit=True)
        plt.tight_layout()
        plt.show()
    
    def close(self):
        """Close oscilloscope connection."""
        if hasattr(self, 'scope'):
            self.scope.close()
        self.rm.close()