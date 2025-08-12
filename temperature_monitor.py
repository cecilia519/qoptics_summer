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

'''
Class to continually collect voltage from Labjack U3 connected to ion gauge and convert to pressure.
Parent class in 'abstract_monitor.py' will save to file.
'''
class temp_monitor(abstract_monitor.dataCollector):
    def __init__(self):
        SAMPLE_RATE = 5         # sample every SAMPLE_RATE seconds
        self.headers = ['Up temp (C)', 'Mid temp (C)']
        self.which = 'up'
        self.therm_data = self.getThermistorData()

        print(self.therm_data)
        # return
        super().__init__(self.headers, saveFilePrefix, SAMPLE_RATE)
        try:
            # ljs=LabJackPython.listAll(deviceType=3)
            # print(f"Available LabJacks: {ljs}")
            self.d = u3.U3(firstFound=False, serial=serial)
        except Exception as e:
            self.d = None
            print(f"Error initializing temperature_monitor: {e}")
            sys.exit(1)
        

    
    def getThermistorData(self):
        """Based on 'pyTemperatureMonitor39k' by Jiayun Schmider
           Reads thermistor data."""
        try:
            df = pd.read_csv(datasheet)
            lol = interp1d(df["Resistance"].to_numpy()[::-1], df["Temperature"].to_numpy()[::-1])
        except Exception as e:
            print(f"Error reading thermistor data: {e}")
        return lol


    def convertVoltToTemp(self, mv):
        """
        Convert voltage reading to temperature. Conversion based on provided datasheet.
        """
        print(mv)
        try:
            v = float(mv / 1000.0)
            if self.which == 'up':
                r0=resAin0
                self.which='mid'
            else:
                r0=resAin1
                self.which='up'

            r = (r0 * v) / (vin - v)
            print(f'r {r}')
            temp = float(self.therm_data(r))
            return temp
        except Exception as oops:
            print(oops)
            raise


    
    
    def getData(self, *args):
        try:
            upVolt = self.d.getAIN(0)
            midVolt = self.d.getAIN(1)
            upTemp = self.convertVoltToTemp(upVolt)  
            midTemp = self.convertVoltToTemp(midVolt)  
            data = [upTemp, midTemp]
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
