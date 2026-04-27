# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 18:18:48 2026

@author: tea
"""
from DHO804logger_fast import RigolDHO804Logger

logger = RigolDHO804Logger()

# Benchmark first to see speeds
logger.benchmark()

# Fast stats collection (can be 100+ Hz)
logger.monitor_and_log_fast(channels=[1, 2], interval=0.01, duration=10, use_stats=True)

# Faster full waveforms with binary
logger.monitor_and_log_fast(channels=[1, 2], interval=0.5, duration=10, use_stats=False)

logger.close()