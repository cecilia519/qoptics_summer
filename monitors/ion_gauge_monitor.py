'''
ion_gauge_monitor.py
================================
Cecilia Soroco 2025
cecilia.soroco@mail.utoronto.ca

Script to monitor Ion Gauge pressure using a LabJack U3-HV device. Will open a new file for saved data every 24h.
Ion Gauge: GP-307Controller307024-MAN with 0.1mA filament current.
'''

import u3
import numpy as np

import sys, os
original_path = os.getcwd()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import abstract_monitor
os.chdir(original_path)

saveFilePrefix=f'ion_gauge_pressure_data'

'''
Class to continually collect voltage from Labjack U3 connected to ion gauge and convert to pressure.
Parent class in 'abstract_monitor.py' will save to file.
'''
class ion_gauge_monitor(abstract_monitor.dataCollector):
    def __init__(self):
        SAMPLE_RATE = 120         # sample every SAMPLE_RATE seconds
        self.headers = ['Pressure (Torr)', 'Voltage (V)']
        super().__init__(self.headers, saveFilePrefix, SAMPLE_RATE)
        try:
            self.d = u3.U3()
        except Exception as e:
            self.d = None
            print(f"Error initializing ion_gauge_monitor: {e}")
            sys.exit(1)
        

    def convertVoltToPressure(self, v):
        """
        Convert voltage reading to pressure in Torr.
        The conversion formula is based on the GP-307 manual, page 20 using current=0.1mA
        """
        n=10  
        P=10**(v-n)
        return P
    
    
    def getData(self, *args):
        try:
            voltage = self.d.getAIN(3)
            pressure = self.convertVoltToPressure(voltage)  
            data = [pressure, voltage]
            return data
        except Exception as e:
            print("Could not read from labjack.")
            raise
        



if __name__ == "__main__":
    monitor = ion_gauge_monitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.data_saver.stop()
        print("Data collection stopped.")
    except Exception as e:
        monitor.data_saver.stop()
        print(f"Error: {e}")
