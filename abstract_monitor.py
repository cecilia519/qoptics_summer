'''
abstract_monitor.py
================================
Cecilia Soroco 2025
cecilia.soroco@mail.utoronto.ca

Script to monitor some source and save data to file. Will open a new file for saved data every 24h.
'''

import csv
import os
import numpy as np
import threading

import time
import schedule
from datetime import datetime

from abc import ABC, abstractmethod


'''
Abstract class to continually collect data from a source and process it.
'''
class dataCollector(ABC):
    def __init__(self, headers, saveFilePrefix, SAMPLE_RATE = 120):
        try:
            self.SAMPLE_RATE = SAMPLE_RATE
            self.data_saver = fileSaver(headers, saveFilePrefix)
        except Exception as e:
            print(f"Error in dataCollector: {e}")
            return    


    @abstractmethod
    def getData(self, *args):
        print("Override this method in child instance")


    def run(self, *args):
        self.data_saver.start()
        while True:
            try:
                data = self.getData(*args)
                assert len(data) == len(self.headers), \
                       f"Length {len(data)} of data doesn't match number of columns {len(self.headers)}"
                self.data_saver.saveToFile(data)  
                time.sleep(self.SAMPLE_RATE)

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.SAMPLE_RATE)
                self.data_saver.saveToFile([-1, -1])  # Save error state with dummy values
                

'''
Class to save pressure and voltage data to a file. Creates a new file named with timestamp every 24 hours.
'''
class fileSaver:
    def __init__(self, headers, saveFilePrefix):
        self.headers = ['Timestamp'] + headers
        self.saveFilePrefix=saveFilePrefix
        self.backups = []
        self.newFile()
        schedule.every().day.at("00:00").do(self.newFile) 
        # schedule.every(24).hours.do(self.newFile) 
        # schedule.every(1).minutes.do(self.newFile)  # For testing, create a new file every minute


    def start(self):
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
       

    def newFile(self):
        '''
        Creates a new file for data saving.
        '''
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_file = f"{self.saveFilePrefix}_{timestamp}.csv"
        self.save_file = new_file
        
        if not os.path.isfile(new_file) or os.stat(new_file).st_size == 0:
            with open(new_file, "w") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
    

    def saveToFile(self, data):
        """
        Save a row of data with timestamp to file.
        A timestamp will get appended to data when saving. 
        """

        data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + data
        if len(data) != len(self.headers):
            print(f"Number of data to write {len(data)} doesn't match number of columns {len(self.headers)}")
            return
        row = dict(zip(self.headers, data))

        try:
            with open(self.save_file, "a", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writerow(row)
        except Exception as e:
            print("Error saving to file (maybe someone is reading).", e)
            self.backups.append(row)