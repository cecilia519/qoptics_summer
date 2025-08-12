'''
ion_gauge_monitor.py
================================
Cecilia Soroco 2025
cecilia.soroco@mail.utoronto.ca

Adapted from pyTempMonitor.pyw
Script to monitor thermoster temperatures using a LabJack U3-HV device. Will open a new file for saved data every midnight.

'''

import u3
import LabJackPython
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

import sys, os
original_path = os.getcwd()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../monitoring_code')))
import abstract_monitor
os.chdir(original_path)

saveFilePrefix= f'temperature_data'
serial        = '320042971'
datasheet     = 'thermistor-datasheet-50k.csv'
vin           = 2.4 #V
resAin0       = 9.14
resAin1       = 9.16
supply        = 'DAC0'

'''
Class to continually collect voltage from Labjack U3 connected to ion gauge and convert to pressure.
Parent class in 'abstract_monitor.py' will save to file.
'''
class temp_monitor(abstract_monitor.dataCollector):
    def __init__(self):
        SAMPLE_RATE = 5         # sample every SAMPLE_RATE seconds
        self.headers = ['Up temp (C)', 'Up res (kOhm)', 'Mid temp (C)', 'Mid res (kOhm)']
        self.which = 'up'
        self.therm_data = self.getThermistorData()
        super().__init__(self.headers, saveFilePrefix, SAMPLE_RATE)
        try:
            # ljs=LabJackPython.listAll(deviceType=3)
            # print(f"Available LabJacks: {ljs}")
            self.d = u3.U3(firstFound=False, serial=serial)
            print("Labjack found! Running...")
        except Exception as e:
            self.d = None
            print(f"Error initializing temperature_monitor: {e}")
            sys.exit(1)
        

    '''
    t7 results:
    roughly steady temp readings
    up: 53.15C, 16.7713 kOhm, 1504mV
    mid: 51.46C, 17.8283, 1539mV
    
    '''
    def getThermistorData(self):
        """Based on 'pyTemperatureMonitor39k' by Jiayun Schmider
           Reads thermistor data."""
        try:
            df = pd.read_csv(datasheet)
            lol = interp1d(df["Resistance"].to_numpy()[::-1], df["Temperature"].to_numpy()[::-1])
        except Exception as e:
            print(f"Error reading thermistor data: {e}")
        return lol


    def convertVoltToTemp(self, v):
        """
        Convert voltage reading to temperature. Conversion based on provided datasheet.
        """
        try:
            if self.which == 'up':
                r0=resAin0
                self.which='mid'
            else:
                r0=resAin1
                self.which='up'

            r = (r0 * v) / (vin - v)
            temp = float(self.therm_data(r))
            # print(f"v {v}, vin {vin}, r1 {r0}, r {r}, temp {temp}")
            return temp, r
        except Exception as oops:
            print(oops)
            raise

    
    
    def getData(self, *args):
        try:
            DAC0_VALUE = self.d.voltageToDACBits(volts=vin, dacNumber=0, is16Bits=False)
            self.d.getFeedback(u3.DAC0_8(DAC0_VALUE)) 

            upVolt = self.d.getAIN(0)
            midVolt = self.d.getAIN(1)

            upTemp, upRes = self.convertVoltToTemp(upVolt)  
            midTemp, midRes = self.convertVoltToTemp(midVolt)  
            data = [upTemp, upRes, midTemp, midRes]
            return data
        except Exception as e:
            print("Error getting/processing could not read from labjack.")
            raise
        



if __name__ == "__main__":
    monitor = temp_monitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.data_saver.stop()
        print("Data collection stopped.")
    except Exception as e:
        monitor.data_saver.stop()
        print(f"Error: {e}")
