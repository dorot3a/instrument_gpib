# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:03:59 2026

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

class OscilloscopeLogger:
    def __init__(self, visa_address=None, timeout=5000):
        """
        Initialize oscilloscope connection via SCPI.
        
        Args:
            visa_address: VISA resource string (e.g., 'USB0::0x1AB1::0x0588::DS1K123456::INSTR')
                         If None, auto-searches for connected devices
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
        
        self.scope = self.rm.open_default_resource(visa_address)
        self.scope.timeout = timeout
        
        idn = self.scope.query("*IDN?")
        print(f"Connected to: {idn}")
    
    def get_waveform_data(self, channel=1):
        """Retrieve waveform data from specified channel."""
        self.scope.write(f":DATA:SOURCE CH{channel}")
        
        time_div = float(self.scope.query(":TIMebase:SCALE?"))
        volt_div = float(self.scope.query(f":CH{channel}:SCALE?"))
        sample_rate = float(self.scope.query(":ACQuire:SRATe?"))
        record_length = int(self.scope.query(":ACQuire:MDEPTH?"))
        
        self.scope.write(":DATA:ENCoding ASCii")
        raw_data = self.scope.query(":DATA:VALues?")
        voltage_data = np.array([float(x) for x in raw_data.split(',')])
        
        time_data = np.arange(len(voltage_data)) / sample_rate
        
        metadata = {
            'channel': channel,
            'time_div': time_div,
            'volt_div': volt_div,
            'sample_rate': sample_rate,
            'record_length': record_length,
            'timestamp': datetime.now().isoformat()
        }
        
        return {'time': time_data, 'voltage': voltage_data, 'metadata': metadata}
    
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
                            waveform = self.get_waveform_data(ch)
                            voltage = waveform['voltage']
                            row_data[f'CH{ch}_mean'] = float(np.mean(voltage))
                            row_data[f'CH{ch}_min'] = float(np.min(voltage))
                            row_data[f'CH{ch}_max'] = float(np.max(voltage))
                            row_data[f'CH{ch}_rms'] = float(np.sqrt(np.mean(voltage**2)))
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
    
    def live_plot(self, channels=[1], duration=60, update_interval=500):
        """
        Display live waveform plots from oscilloscope.
        
        Args:
            channels: List of channels to plot
            duration: Total display duration in seconds (None = continuous)
            update_interval: Matplotlib update interval in milliseconds
        """
        num_channels = len(channels)
        fig, axes = plt.subplots(num_channels, 1, figsize=(12, 4*num_channels))
        
        # Handle single channel case
        if num_channels == 1:
            axes = [axes]
        
        fig.suptitle('Oscilloscope Live Monitor', fontsize=14, fontweight='bold')
        
        # Store line objects and data buffers
        lines = []
        data_buffers = {}
        start_time = time.time()
        
        for idx, ch in enumerate(channels):
            ax = axes[idx]
            line, = ax.plot([], [], lw=2, color=f'C{idx}')
            lines.append(line)
            data_buffers[ch] = {'time': deque(maxlen=1000), 'voltage': deque(maxlen=1000)}
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(f'Voltage (V)')
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
                    
                    # Append new data
                    for t, v in zip(time_data, voltage_data):
                        data_buffers[ch]['time'].append(t)
                        data_buffers[ch]['voltage'].append(v)
                    
                    # Update line
                    lines[idx].set_data(data_buffers[ch]['time'], data_buffers[ch]['voltage'])
                    
                    # Auto-scale axes
                    ax = axes[idx]
                    ax.relim()
                    ax.autoscale_view()
                    
                    # Update title with stats
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
    
    def live_plot_with_logging(self, channels=[1], interval=1.0, 
                               duration=None, filename='oscilloscope_data.csv',
                               update_interval=500):
        """
        Monitor, log to CSV, and display live plots simultaneously.
        
        Args:
            channels: List of channels to monitor
            interval: Sampling interval in seconds
            duration: Total monitoring duration in seconds
            filename: Output CSV filename
            update_interval: Plot update interval in milliseconds
        """
        csv_file = Path(filename)
        start_time = time.time()
        sample_count = 0
        
        # Setup plot
        num_channels = len(channels)
        fig, axes = plt.subplots(num_channels, 1, figsize=(12, 4*num_channels))
        if num_channels == 1:
            axes = [axes]
        
        fig.suptitle('Oscilloscope Monitor with Logging', fontsize=14, fontweight='bold')
        
        lines = []
        data_buffers = {}
        
        for idx, ch in enumerate(channels):
            ax = axes[idx]
            line, = ax.plot([], [], lw=2, color=f'C{idx}')
            lines.append(line)
            data_buffers[ch] = {'time': deque(maxlen=1000), 'voltage': deque(maxlen=1000)}
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Voltage (V)')
            ax.set_title(f'Channel {ch}')
            ax.grid(True, alpha=0.3)
        
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = None
                last_update = time.time()
                
                while True:
                    elapsed = time.time() - start_time
                    if duration and elapsed > duration:
                        break
                    
                    row_data = {'timestamp': datetime.now().isoformat()}
                    
                    for ch in channels:
                        try:
                            waveform = self.get_waveform_data(ch)
                            voltage = waveform['voltage']
                            
                            # Store for logging
                            row_data[f'CH{ch}_mean'] = float(np.mean(voltage))
                            row_data[f'CH{ch}_min'] = float(np.min(voltage))
                            row_data[f'CH{ch}_max'] = float(np.max(voltage))
                            row_data[f'CH{ch}_rms'] = float(np.sqrt(np.mean(voltage**2)))
                            
                            # Store for plotting
                            if time.time() - last_update > update_interval / 1000:
                                time_data = waveform['time']
                                for t, v in zip(time_data, voltage):
                                    data_buffers[ch]['time'].append(t)
                                    data_buffers[ch]['voltage'].append(v)
                        
                        except Exception as e:
                            print(f"Error reading CH{ch}: {e}")
                    
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=row_data.keys())
                        writer.writeheader()
                    
                    writer.writerow(row_data)
                    sample_count += 1
                    
                    # Update plot
                    if time.time() - last_update > update_interval / 1000:
                        for idx, ch in enumerate(channels):
                            lines[idx].set_data(data_buffers[ch]['time'], data_buffers[ch]['voltage'])
                            axes[idx].relim()
                            axes[idx].autoscale_view()
                            
                            if len(data_buffers[ch]['voltage']) > 0:
                                v_data = np.array(data_buffers[ch]['voltage'])
                                mean_v = np.mean(v_data)
                                max_v = np.max(v_data)
                                min_v = np.min(v_data)
                                axes[idx].set_title(f'Channel {ch} | Mean: {mean_v:.3f}V | '
                                                   f'Max: {max_v:.3f}V | Min: {min_v:.3f}V')
                        
                        fig.canvas.draw_idle()
                        plt.pause(0.001)
                        last_update = time.time()
                    
                    print(f"Sample {sample_count} recorded at {row_data['timestamp']}")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            print(f"\nMonitoring stopped. {sample_count} samples saved to {csv_file}")
        finally:
            plt.close()
            self.close()
    
    def save_single_waveform(self, channel=1, filename=None):
        """Save full waveform from single channel to CSV."""
        waveform = self.get_waveform_data(channel)
        
        if filename is None:
            filename = f"CH{channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time (s)', f'Voltage CH{channel} (V)'])
            writer.writerows(zip(waveform['time'], waveform['voltage']))
        
        print(f"Waveform saved to {filename}")
    
    def close(self):
        """Close oscilloscope connection."""
        if hasattr(self, 'scope'):
            self.scope.close()
        self.rm.close()