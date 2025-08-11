'''
Script for saving data and visualizing in real time. Creates a new file every 24 hours.

Cecilia Soroco 2025
cecilia.soroco@mail.utoronto.ca
'''
import csv
import os
import numpy as np
import schedule
import time

from datetime import datetime

'''
Class to save pressure and voltage data to a file. Creates a new file named with timestamp every 24 hours.
'''
class fileSaver:
    def __init__(self):
        self.headers = ['Timestamp', 'Pressure (Torr)', 'Voltage (V)']
        self.newFile()
        schedule.every(24).hours.do(self.newFile) 

        while True:
            schedule.run_pending()
            time.sleep(1)

       
    def newFile(self):
        '''
        Creates a new file for data saving.
        '''
        timestamp= datetime.now().strftime("%Y-%m-%d")
        new_file=f"pressure_data_{timestamp}.csv"
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
