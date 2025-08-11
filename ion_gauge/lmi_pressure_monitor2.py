'''
lmi_pressure_monitor.py
================================
Cecilia Soroco 2025
cecilia.soroco@mail.utoronto.ca

Script to monitor Ion Gauge pressure using a LabJack U3-HV device. Will open a new file for saved data every 24h.
Ion Gauge: GP-307Controller307024-MAN with 0.1mA filament current.
'''

import u3

import csv
import os
import numpy as np
import threading

import time
import schedule
from datetime import datetime

saveFilePrefix=f'Pressure_data'

'''
Class to continually collect voltage from Labjack U3 connected to ion gauge and convert to pressure
'''
class dataCollector:
    def __init__(self):
        try:
            self.SAMPLE_RATE = 5         # sample every SAMPLE_RATE seconds
            self.data_saver = fileSaver()
            self.d = u3.U3()
        except Exception as e:
            self.d = None
            print(f"Error: {e}")
            return


    def convertVoltToPressure(self, v):
        """
        Convert voltage reading to pressure in Torr.
        The conversion formula is based on the GP-307 manual, page 20 using current=0.1mA
        """
        n=10  
        P=10**(v-n)
        return P
    

    def run(self):
        while True:
            try:
                voltage = self.d.getAIN(3)
                pressure = self.convertVoltToPressure(voltage)  
                self.data_saver.saveToFile(pressure, voltage)  
                time.sleep(self.SAMPLE_RATE)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.SAMPLE_RATE)
                self.data_saver.saveToFile(-1, -1)  # Save error state with dummy values
                

'''
Class to save pressure and voltage data to a file. Creates a new file named with timestamp every 24 hours.
'''
class fileSaver:
    def __init__(self):
        self.headers = ['Timestamp', 'Pressure (Torr)', 'Voltage (V)']
        self.newFile(saveFilePrefix)
        # schedule.every(24).hours.do(self.newFile) 
        schedule.every(1).minutes.do(self.newFile)  # For testing, create a new file every minute

        self.running = True
        self.thread = threading.Thread(target=self.run_schedule_loop, daemon=True) # daemon=True allows the thread to exit when the main program exits
        self.thread.start()


    def run_schedule_loop(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)


    def stop(self):
        self.running = False
        self.thread.join()
        print("Threads joined.")
       

    def newFile(self, saveFilePrefix=saveFilePrefix):
        '''
        Creates a new file for data saving.
        '''
        # timestamp= datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_file = f"{saveFilePrefix}_{timestamp}.csv"
        self.save_file = new_file
        
        if not os.path.isfile(new_file) or os.stat(new_file).st_size == 0:
            with open(new_file, "w") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
    

    def saveToFile(self, pressure, voltage):
        """
        Save the pressure and voltage readings to a file.
        """
        with open(self.save_file, "a") as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow({
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Pressure (Torr)': f"{pressure:.12f}",
                'Voltage (V)': voltage
            })


if __name__ == "__main__":
    collector = dataCollector()
    try:
        collector.run()
    except KeyboardInterrupt:
        collector.data_saver.stop()
        print("Data collection stopped.")
    except Exception as e:
        collector.data_saver.stop()
        print(f"Error: {e}")
