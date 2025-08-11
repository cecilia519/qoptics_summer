import numpy as np
import serial
import os, sys

original_path = os.getcwd()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import abstract_monitor
os.chdir(original_path)

'''
Commands
*[QUERY   CHAR]?        is query
*[COMMAND CHAR]:[VALUE] is command


PIN 2 TxD
PIN 3 RxD
PIN 5 COMMON
PIN 8 RTS (request to send) (from ion to computer)
PIN 7 CTS (clear to send)  (from computer back to ion)


A script to continuously query pressure via serial port reading.
Every N seconds, run .txt file for query.

Terranova 751A

'''

saveFilePrefix = 'ion_pump_pressure'

class ion_pump_monitor(abstract_monitor.dataCollector):
    def __init__(self):
        self.QUERY_CHARS = ['MO', 'VE', 'ST', 'HV', 'PO', 'VP', 'CU', 
                            'PR', 'SP', 'MV', 'MC', 'PS', 'UN']
        self.COMMAND_CHARS = ['SP', 'MV', 'MC', 'PS', 'UN', 'HV']
        self.port = "COM6"  # Find available ports: 'python -m serial.tools.list_ports'
        self.pressure_query = '*PR?\r\n'
        self.status_query   = '*ST?\r\n'
        self.WAIT_TIME = 10       # seconds
        self.headers = ['Pressure (Torr)']
        super().__init__(self.headers, saveFilePrefix, self.WAIT_TIME)


    def getData(self, *args):
        ser = args[0]
        try:
            ser.write(self.pressure_query.encode('utf-8'))
            ser.flush()             # clear input buffer, waits until all data is written
            data = ser.read(16).decode()      # Reads 1 byte or times out
            if len(data) > 0:   
                print(f"Received data: {data}")
                data = self.cleanData(data)
                return [data]
            else:
                print("No serial data received.")  
        except serial.SerialException as e:
            print(f"Serial error") 
            raise
        
    def cleanData(self, data):
        ''' Takes data 'OK:<PRESSURE>,##' and return only <PRESSURE>'''
        # print(data[0:5])
        print(str(data))
        data = str(data)
        data = data.split(":")[1].split(",")[0]
        return data

    def run(self):
        '''
            Opens serial port, checks status, and sends to parent class to run
        '''
        try:
            with serial.Serial(self.port, 9600, timeout = 0.5) as ser:
                ser.write(self.status_query.encode('utf-8'))
                ser.flush()             # clear input buffer, waits until all data is written
                status = ser.read(16).decode()      # Reads 1 byte or times out
                print(f"Status: ", status)
                super().run(ser)
            ser.close()
        except Exception as e:
            print(f"Error in ion_pump_monitor", e)



if __name__ == "__main__":
    monitor = ion_pump_monitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.data_saver.stop()
        print("Data collection stopped.")
    except Exception as e:
        monitor.data_saver.stop()
        print(f"Error: {e}")

