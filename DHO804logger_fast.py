# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 18:17:30 2026

@author: tea
"""

import pyvisa
import csv
import time
from datetime import datetime
from pathlib import Path
import numpy as np
import struct

class RigolDHO804Logger:
    def __init__(self, visa_address=None, timeout=2000):
        """
        Initialize Rigol DHO804 with optimized settings for fast data collection.
        
        Args:
            visa_address: VISA resource string
            timeout: Communication timeout in milliseconds (reduced to 2 seconds)
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
        
        # Cache channel settings to avoid repeated queries
        self.channel_cache = {}
    
    def get_waveform_data_fast(self, channel=1, use_binary=True):
        """Retrieve waveform data as fast as possible."""
        try:
            # Set source
            self.scope.write(f":WAVeform:SOURce CH{channel}")
            
            # Use binary format for speed (10x faster than ASCII)
            if use_binary:
                self.scope.write(":WAVeform:FORMat BYTE")
                self.scope.write(":WAVeform:DATA?")
                raw_data = self.scope.read_raw()
                voltage_data = np.frombuffer(raw_data, dtype=np.uint8).astype(float)
            else:
                self.scope.write(":WAVeform:FORMat ASCII")
                self.scope.write(":WAVeform:DATA?")
                raw_data = self.scope.read()
                voltage_data = np.array([float(x) for x in raw_data.split(',')])
            
            # Get sample rate (cache this as it doesn't change often)
            if channel not in self.channel_cache:
                sample_rate = float(self.scope.query(":WAVeform:SRATe?"))
                time_div = float(self.scope.query(":TIMebase:MAIN:SCALe?"))
                volt_div = float(self.scope.query(f":CHANnel{channel}:SCALe?"))
                
                self.channel_cache[channel] = {
                    'sample_rate': sample_rate,
                    'time_div': time_div,
                    'volt_div': volt_div
                }
            
            cached = self.channel_cache[channel]
            time_data = np.arange(len(voltage_data)) / cached['sample_rate']
            
            return {
                'time': time_data,
                'voltage': voltage_data,
                'metadata': {
                    'channel': channel,
                    'sample_rate': cached['sample_rate'],
                    'timestamp': datetime.now().isoformat()
                }
            }
        
        except Exception as e:
            print(f"Error reading CH{channel}: {e}")
            raise
    
    def get_channel_stats_fast(self, channel=1):
        """Get stats quickly without full waveform transfer."""
        try:
            # Single query for mean instead of separate queries
            mean = float(self.scope.query(f":MEASure:STAT:MEAN? CH{channel}"))
            max_val = float(self.scope.query(f":MEASure:STAT:MAX? CH{channel}"))
            min_val = float(self.scope.query(f":MEASure:STAT:MIN? CH{channel}"))
            
            return {'mean': mean, 'max': max_val, 'min': min_val}
        except:
            return None
    
    def monitor_and_log_fast(self, channels=[1, 2], interval=0.1, 
                             duration=None, filename='oscilloscope_data.csv',
                             use_stats=True):
        """
        Fast logging with minimal overhead.
        
        Args:
            channels: List of channels to monitor
            interval: Sampling interval in seconds (0.1 = 10 Hz)
            duration: Total monitoring duration in seconds
            filename: Output CSV filename
            use_stats: If True, log only stats (fast). If False, log full waveforms (slower).
        """
        csv_file = Path(filename)
        start_time = time.time()
        sample_count = 0
        
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = None
                
                while True:
                    loop_start = time.time()
                    elapsed = time.time() - start_time
                    
                    if duration and elapsed > duration:
                        break
                    
                    row_data = {'timestamp': datetime.now().isoformat()}
                    
                    for ch in channels:
                        try:
                            if use_stats:
                                stats = self.get_channel_stats_fast(ch)
                                if stats:
                                    row_data[f'CH{ch}_mean'] = stats['mean']
                                    row_data[f'CH{ch}_min'] = stats['min']
                                    row_data[f'CH{ch}_max'] = stats['max']
                            else:
                                # Full waveform
                                waveform = self.get_waveform_data_fast(ch, use_binary=True)
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
                    
                    # Calculate actual loop time
                    loop_time = time.time() - loop_start
                    actual_interval = interval - loop_time
                    
                    if sample_count % 10 == 0:
                        print(f"Sample {sample_count}: {loop_time:.3f}s/sample")
                    
                    if actual_interval > 0:
                        time.sleep(actual_interval)
        
        except KeyboardInterrupt:
            print(f"\nLogging stopped. {sample_count} samples saved to {csv_file}")
        finally:
            self.close()
    
    def benchmark(self):
        """Measure data collection speed."""
        print("Benchmarking data collection speeds...\n")
        
        for ch in [1, 2]:
            # ASCII format
            start = time.time()
            try:
                self.scope.write(":WAVeform:FORMat ASCII")
                waveform = self.get_waveform_data_fast(ch, use_binary=False)
                ascii_time = time.time() - start
                print(f"CH{ch} ASCII: {ascii_time:.3f}s ({len(waveform['voltage'])} points)")
            except:
                pass
            
            # Binary format
            start = time.time()
            try:
                self.scope.write(":WAVeform:FORMat BYTE")
                waveform = self.get_waveform_data_fast(ch, use_binary=True)
                binary_time = time.time() - start
                print(f"CH{ch} BINARY: {binary_time:.3f}s ({len(waveform['voltage'])} points)")
            except:
                pass
            
            # Stats only
            start = time.time()
            stats = self.get_channel_stats_fast(ch)
            stats_time = time.time() - start
            print(f"CH{ch} STATS: {stats_time:.3f}s\n")
    
    def close(self):
        """Close oscilloscope connection safely."""
        try:
            if hasattr(self, 'scope') and self.scope:
                self.scope.clear()
                self.scope.close()
                print("Scope closed")
        except Exception as e:
            print(f"Error closing scope: {e}")
        
        try:
            if hasattr(self, 'rm') and self.rm:
                self.rm.close()
        except Exception as e:
            print(f"Error closing resource manager: {e}")