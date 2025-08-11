'''
lmi_pressure_monitor.py
================================
Cecilia Soroco 2025
Adapted from 'https://github.com/labjack/LabJackPython/blob/master/Examples/streamTest.py'

Script to monitor stream of data from Ion Gauge pressure using a LabJack U3 device.
Expect data scanning in 1Hz-1000Hz range. If less is required, use lmi_pressure_monitor.py.

Ion Gauge: GP-307Controller307024-MAN with 0.1mA filament current.
Documentation for streaming: 'https://support.labjack.com/docs/streamconfig'
'''

import sys
import traceback
from datetime import datetime
import u3

from queue import Queue
from threading import Thread

import numpy as np



MAX_REQUESTS = 75
SCAN_TIME = 30 # seconds
SCAN_FREQUENCY = int(np.ceil(1 / SCAN_TIME)) # Scans / second
NUM_CHANNELS = 1
data_queue = Queue()


def convertVoltToPressure(v):
    """
    Convert voltage reading to pressure in Torr.
    The conversion formula is based on the GP-307 manual, page 20 using current=0.1mA
    """
    n=10  
    P=10**(v-n)
    return P

def processData(r):
    """
    Process the data read from the stream. Send to lmi_pressure_data.py for saving
    """
    AIN3 = r["AIN3"]
    lastPoint=AIN3[-1] # get last point
    pressure = convertVoltToPressure(lastPoint)
    print(f"Pressure: {pressure} Torr, Voltage: {lastPoint} V")
    
    import lmi_pressure_data_saver as lmi_data
    lmi_data.saveToFile(pressure, lastPoint, 'pressure_data_stream.csv') 


def process_worker():
    while True:
        r = data_queue.get()
        if r is None:
            break
        processData(r)
        data_queue.task_done()

# Start processor thread
worker = Thread(target=process_worker, daemon=True)
worker.start()

d = u3.U3()
d.configU3()                # To learn if the U3 is an HV
d.getCalibrationData()      # For applying the proper calibration to readings.
d.configIO(FIOAnalog=8)     # bitmask, only AIN3 is available.

print("Configuring U3 stream")
d.streamConfig(NumChannels=NUM_CHANNELS, PChannels=[3], NChannels=[31], Resolution=3, ScanFrequency=SCAN_FREQUENCY)
# default samplesPerPacket = 25, packetsPerRequest = 1 <= freq/SamplesPerPacket <= 48
# NChannel=[31] is code for single-pin. Ie. will compare PChannel to ground (not some other pin).
#################################################################################################
if d is None:
    print("""Configure a device first. Exiting...""")
    sys.exit(0)
try:
    print("Start stream")
    d.streamStart()
    start = datetime.now()
    print("Start time is %s" % start)

    missed = 0
    dataCount = 0
    packetCount = 0

    for r in d.streamData():
        if r is not None:
            if dataCount >= MAX_REQUESTS:
                break

            if r["errors"] != 0:
                print("Errors counted: %s ; %s" % (r["errors"], datetime.now()))

            if r["numPackets"] != d.packetsPerRequest:
                print("----- UNDERFLOW : %s ; %s" %
                      (r["numPackets"], datetime.now()))

            if r["missed"] != 0:
                missed += r['missed']
                print("+++ Missed %s" % r["missed"])

            data_queue.put(r)
            dataCount += 1
            packetCount += r['numPackets']
        else:
            # Got no data back from our read.
            # This only happens if your stream isn't faster than the USB read
            # timeout, ~1 sec.
            print("No data ; %s" % datetime.now())
except:
    print("".join(i for i in traceback.format_exc()))
finally:
    stop = datetime.now()
    d.streamStop()
    print("Stream stopped.\n")
    d.close()

    data_queue.put(None) 
    worker.join()

    sampleTotal = packetCount * d.streamSamplesPerPacket
    scanTotal = sampleTotal / NUM_CHANNELS
    print("%s requests with %s packets per request with %s samples per packet = %s samples total." %
          (dataCount, (float(packetCount)/dataCount), d.streamSamplesPerPacket, sampleTotal))
    print("%s samples were lost due to errors." % missed)
    sampleTotal -= missed
    print("Adjusted number of samples = %s" % sampleTotal)

    runTime = (stop-start).seconds + float((stop-start).microseconds)/1000000
    print("The experiment took %s seconds." % runTime)
    print("Actual Scan Rate = %s Hz" % SCAN_FREQUENCY)
    print("Timed Scan Rate = %s scans / %s seconds = %s Hz" %
          (scanTotal, runTime, float(scanTotal)/runTime))
    print("Timed Sample Rate = %s samples / %s seconds = %s Hz" %
          (sampleTotal, runTime, float(sampleTotal)/runTime))

