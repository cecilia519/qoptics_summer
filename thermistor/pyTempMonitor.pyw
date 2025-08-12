"""
pyTemperatureMonitor39k
--------------------
Jiayun Schmider
jiayun.schmider@mail.physics.utoronto.ca

Based on "pyTemperatureMonitor" by
Shreyas Potnis
spotnis@physics.utoronto.ca

Description:
------------
This application is designed to monitor and log temperature readings using one or more LabJack U3-HV device(s). Provides
GUI built with Tkinter, displaying real-time temperature and voltage readings from multiple channels. The application
supports setting alarm thresholds for temperature, with email notifications sent if thresholds are exceeded.

Required packages
-----------------------
labjackpython - http://labjack.com/support/labjackpython
matplotlib
tkinter
numpy
scipy
smtplib

Hardware
--------
Has been tested on Labjack U3-HV. See function read() or labjack to get it working on other models
"""


import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import smtplib
from email.mime.text import MIMEText

import pandas as pd
import numpy as np
from datetime import datetime

import configparser
import labjack
import logger

directory = "C:/Users/Josiah/Dropbox/LMI Project/2024_MOT_failure/baking/39kHeatMonitoringCode/"

plt.style.use('bmh')

class MainWindow(tk.Tk):
    """The main class of the program. All windows, dialogs, and plots are
    children of this class.
    """

    def __init__(self, config, internal_config):
        """Initialize the MainWindow and application settings."""
        super().__init__()
        self.temp_interpolate_50k = None
        self.config = config
        self.internal_config = internal_config
        self.title('Py-Temperature Monitor-LMI')
        self.geometry('800x600')

        # Initialize LabJack and Logging
        self.ljs = labjack.LabJackManager()
        print(self.ljs)
        print(self.ljs.getKeys())
        self.ljsID = self.ljs.getKeys()
        self.all_channels = self.ljs.getAllChannels()
        self.getConfig()
        self.ljs.configure(self.read_channels)
        self.log = logger.Logger(self.labels, self.log_folder)
        self.getThermistorData()

        # Email settings for alarm notifications
        self.email_settings = {
            'sender': self.config.get('email', 'sender'),
            'recipient': self.config.get('email', 'recipient'),
            'smtp_server': self.config.get('email', 'smtp_server'),
            'smtp_port': self.config.get('email', 'smtp_port'),
            'smtp_user': self.config.get('email', 'smtp_user'),
            'smtp_password': self.config.get('email', 'smtp_password'),
        }
        self.alarm_triggered = {key: [False] * len(self.labels[key]) for key in self.ljsID}

        # Initialize plot data
        self.time_data = []
        self.temp_data = {key: np.zeros((len(self.labels[key]), 0)) for key in self.ljsID}
        self.voltage_data = {key: np.zeros((len(self.labels[key]), 0)) for key in self.ljsID}

        # Create the UI
        self.create_widgets()
        self.iconbitmap(f"{directory}tray_icon.ico")

        # Start the update loop
        self.update_data()

    def getConfig(self):
        """Load and process relevant parameters from the configuration file."""
        self.timer_value = int(1000 / float(self.config.get('settings', 'READ_RATE')))
        self.save_folder = self.config.get('settings', 'SAVE_FOLDER')
        self.log_folder = self.config.get('settings', 'LOG_FOLDER')
        self.log_max = self.config.getint('settings', 'LOG_MAX')

        self.read_channels = {}
        self.labels = {}
        self.max_temps = {}
        self.resistances = {}
        self.device_name = {}
        self.vin = {}

        self.plot_channel = {}

        # Retrieve configuration for each LabJack device
        for key in self.ljsID:
            self.vin[key] = float(self.config.get(key, 'VIN'))
            outputchannel = int(self.config.get(key, 'OUTPUT'))
            self.ljs.setOutput(key, outputchannel, self.vin[key])

            self.read_channels[key] = []
            self.labels[key] = []
            self.max_temps[key] = []
            self.resistances[key] = []
            self.plot_channel[key] = []

            for ch_number, ch_addr in zip(range(len(self.all_channels[key])), self.all_channels[key]):
                try:
                    label = self.config.get(key, ch_addr)
                    max_temp = self.config.get(key, f"max_temp_{ch_number}")
                    resistance = self.config.get(key, f"res_{ch_addr}")
                    ticked = self.internal_config.getboolean(f'checkbox{key}', ch_addr)
                    self.device_name[key] = self.config.get(key, "name")
                    self.read_channels[key].append(ch_number)
                    self.labels[key].append(label)
                    self.max_temps[key].append(float(max_temp))
                    self.resistances[key].append(float(resistance))
                    self.plot_channel[key].append(ticked)
                except configparser.NoOptionError:
                    pass

    def create_widgets(self):
        """Create the UI widgets."""
        self.plot_frame = ttk.Frame(self)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        # Create Matplotlib Figure and Axes
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.figure.tight_layout(pad=2.5)

        # Add FigureCanvas to Tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Create controls for temperature boxes
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill=tk.X)

        # Create headers for the controls
        ttk.Label(self.controls_frame, text="Channel Name").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.controls_frame, text="Temperature (°C)").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.controls_frame, text="Resistance (kΩ)").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.controls_frame, text="Voltage (mV)").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.controls_frame, text="Plot ?").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.controls_frame, text="Max Temp (°C)").grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

        # Initialize lists for labels, checkboxes, and entries
        self.temp_labels = {key: [] for key in self.ljsID}
        self.resistance_labels = {key: [] for key in self.ljsID}
        self.voltage_labels = {key: [] for key in self.ljsID}
        self.checkboxes = {key: [] for key in self.ljsID}
        self.max_temp_entries = {key: [] for key in self.ljsID}

        row_posn = 0

        # Populate the UI with channels and their corresponding data
        for i, key in enumerate(self.ljsID):
            row_posn += 1
            ttk.Label(self.controls_frame, text=self.device_name[key]).grid(row=row_posn, column=0, padx=5, pady=1, sticky=tk.W)

            for i, label in enumerate(self.labels[key]):
                row_posn += 1
                ttk.Label(self.controls_frame, text=label).grid(row=row_posn, column=0, padx=5, pady=1, sticky=tk.W)
                temp_label = ttk.Label(self.controls_frame, text='0.0')
                temp_label.grid(row=row_posn, column=1, padx=5, pady=0, sticky=tk.W)
                self.temp_labels[key].append(temp_label)

                resistance_label = ttk.Label(self.controls_frame, text='0')
                resistance_label.grid(row=row_posn, column=2, padx=5, pady=0, sticky=tk.W)
                self.resistance_labels[key].append(resistance_label)

                voltage_label = ttk.Label(self.controls_frame, text='0')
                voltage_label.grid(row=row_posn, column=3, padx=5, pady=0, sticky=tk.W)
                self.voltage_labels[key].append(voltage_label)

                var = tk.BooleanVar(value=self.plot_channel[key][i])
                checkbox = tk.Checkbutton(self.controls_frame, text='', variable=var,
                                                  command=self.checkbox_changed)
                checkbox.grid(row=row_posn, column=4, padx=5, pady=0)
                self.checkboxes[key].append(var)

                max_temp_entry = ttk.Entry(self.controls_frame, width=5)
                max_temp_entry.grid(row=row_posn, column=5, padx=5, pady=0)
                max_temp_entry.insert(0, str(self.max_temps[key][i]))
                self.max_temp_entries[key].append(max_temp_entry)

        # Add "Save Data" button
        save_button = ttk.Button(self.controls_frame, text="Save Data", command=self.save_data)
        save_button.grid(row=row_posn + 1, column=0, columnspan=1, pady=10)

        # Add "Update Max Temps" button
        update_temps_button = ttk.Button(self.controls_frame, text="Update Max Temps", command=self.update_max_temps)
        update_temps_button.grid(row=row_posn + 1, column=5, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_data(self):
        """Periodically read values from LabJack, update display, and log."""
        try:
            voltages = self.ljs.read()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_data.append(current_time)

            for key in self.ljsID:
                temp, resistance = self.processVoltage(voltages[key], key)
                self.temp_data[key] = np.hstack((self.temp_data[key], np.array(temp).reshape(-1, 1)))
                self.voltage_data[key] = np.hstack(
                    (self.voltage_data[key], np.array([v[0] for v in voltages[key]]).reshape(-1, 1)))

                for temp_val, label in zip(temp, self.temp_labels[key]):
                    label.config(text=f'{temp_val:.2f}')
                for res_val, label in zip(resistance, self.resistance_labels[key]):
                    label.config(text=f'{res_val:.4f}')
                for vol_val, label in zip(voltages[key], self.voltage_labels[key]):
                    label.config(text=f'{vol_val[0]:.0f}')
                self.log.log(key, temp)
                self.check_alarms(temp, key)

            self.update_plot()

        except Exception as e:
            print(f"Error occurred: {e}")

        self.after(self.timer_value, self.update_data)

    def update_plot(self):
        """Updates GUI plot"""
        if not self.time_data or not self.temp_data:
            return

        max_points = min(self.log_max, len(self.time_data))

        # Convert time and temp data to suitable format for plotting
        time_array = np.array(self.time_data[-max_points:], dtype='datetime64')
        self.ax.clear()

        # Plot the data
        for key in self.ljsID:
            temp_array = self.temp_data[key][:, -max_points:]
            for i, label in enumerate(self.labels[key]):
                if self.plot_channel[key][i]:
                    self.ax.plot(time_array, temp_array[i], label=label)

        # Set axis labels and title
        self.ax.set_xlabel('Time', fontsize=10)
        self.ax.set_ylabel('Temperature (°C)', fontsize=10)
        self.ax.legend(fontsize=8,loc='upper left')

        # Set date formatting for the x-axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.ax.tick_params(axis='both', which='major', labelsize=8)

        # Set tick locator to limit the number of ticks
        self.ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))

        # Redraw the canvas
        self.canvas.draw()

    def update_max_temps(self):
        """Update max temperatures from the entry fields and save to config."""
        for key, entries in self.max_temp_entries.items():
            try:
                max_temps = [float(entry.get()) for entry in entries]
                self.max_temps[key] = max_temps
                for i, temp in enumerate(max_temps):
                    self.config.set(f'alarm{key}', f'max_temp_{i}', str(temp))
            except ValueError:
                print(f"Invalid temperature value in entries for {key}")

    def save_data(self):
        """Save the raw temperature data and the current plot."""
        try:
            data_df = pd.DataFrame({'Time': self.time_data})
            # Save temperature data to CSV
            for key in self.ljsID:
                temps = self.temp_data[key]
                voltages = self.voltage_data[key]
                for i, label in enumerate(self.labels[key]):
                    data_df[f"{key}_{label}_Temp"] = temps[i]
                    data_df[f"{key}_{label}_Voltage"] = voltages[i]

            temp_filename = datetime.now().strftime("temperature_voltage_data_%Y%m%d_%H%M%S.csv")
            data_df.to_csv(self.save_folder + temp_filename, index=False)
            print(f"Temperature and voltage data saved to {temp_filename}")

            # Save plot to PNG
            plot_filename = datetime.now().strftime("temperature_plot_%Y%m%d_%H%M%S.png")
            self.figure.savefig(self.save_folder + plot_filename)
            print(f"Plot saved to {plot_filename}")

            messagebox.showinfo("Save Data",
                                f"Data and plot have been saved successfully:\n{temp_filename}\n{plot_filename}")

        except Exception as e:
            print(f"Error saving data: {e}")
            messagebox.showerror("Save Data", f"An error occurred while saving data:\n{e}")

    def check_alarms(self, temp, key):
        """Checks if any channels have exceeded set temperature threshold and send alarm if it has(and an alarm has not
         already been sent)"""
        for i, temp_val in enumerate(temp):
            if temp_val > self.max_temps[key][i]:
                if not self.alarm_triggered[key][i]:
                    self.send_alarm_email(key, i, temp_val)
                    self.alarm_triggered[key][i] = True
            else:
                self.alarm_triggered[key][i] = False

    def send_alarm_email(self, key, channel_index, temp_val):
        """Send an alarm email if temperature exceeds max limit."""
        try:
            subject = f"Temperature Alarm on {key}, Channel {self.labels[key][channel_index]}"
            body = f"The temperature on {key}, channel {self.labels[key][channel_index]} has exceeded the limit!\nCurrent temperature: {temp_val:.2f} °C"

            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.email_settings['sender']

            # Handle multiple recipients
            recipients = self.email_settings['recipient'].split(',')
            msg['To'] = ', '.join(recipients)

            with smtplib.SMTP(self.email_settings['smtp_server'], self.email_settings['smtp_port']) as server:
                server.starttls()
                server.login(self.email_settings['smtp_user'], self.email_settings['smtp_password'])
                server.sendmail(self.email_settings['sender'], recipients, msg.as_string())

        except Exception as e:
            print(f"Error occurred while sending alarm email: {e}")

    def getThermistorData(self):
        """Read thermistor data."""
        try:
            df = pd.read_csv(f"{directory}thermistor-datasheet-50k.csv")
            self.temp_interpolate_50k = interp1d(df["Resistance"].to_numpy()[::-1], df["Temperature"].to_numpy()[::-1])
        except Exception as e:
            print(f"Error reading thermistor data: {e}")

    def processVoltage(self, voltages, key):
        """Convert thermocouple voltages to temperature and resistance."""
        temp = []
        resistance = []
        for mV in voltages:
            v = float(mV[0] / 1000.0)
            i = mV[1]
            vin = 2.5# self.vin[key] +.12
            r1 = self.resistances[key][self.read_channels[key].index(i)]
            r = (r1 * v) / (vin - v)
            temp.append(float(self.temp_interpolate_50k(r)))
            resistance.append(r)
        return temp, resistance

    def checkbox_changed(self):
        """Handle checkbox state changes."""

        for key in self.ljsID:
            for i, var in enumerate(self.checkboxes[key]):
                self.plot_channel[key][i] = var.get()
                self.internal_config.set(f'checkbox{key}', self.all_channels[key][i], str(self.plot_channel[key][i]))

            with open('internal_config.ini', 'w') as fp:
                self.internal_config.write(fp)

    def on_closing(self):
        """Handle window close."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.ljs.closeLJ()
            self.destroy()


def main():
    """Main entry point for the application."""
    config = configparser.ConfigParser(allow_no_value=True)
    internal_config = configparser.ConfigParser(allow_no_value=True)
    config.read(f"{directory}config.ini")
    internal_config.read(f"{directory}internal_config.ini")
    app = MainWindow(config, internal_config)
    app.mainloop()


if __name__ == '__main__':
    main()

