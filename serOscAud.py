#!/usr/bin/python3
"""
pyinstaller --clean --onefile --add-data "devcon.exe;." serOscAudTuya.py
"""
import json
import os
import sys
import serial
import time
import serial.tools.list_ports
from pythonosc import udp_client
import subprocess

VERSION="2025.05.09"
print(f"Version: {VERSION}")

def readConfig(settingsFile):
    if os.path.isfile(settingsFile):
        with open(settingsFile) as json_file:
            data = json.load(json_file)
    else:
        data = {
            "uart" : "auto",
	        "baudrate" : 9600,
	        "oscServer" : "127.0.0.1",
            "oscPort" : 8010,
            "idleAddress" : "/idle",
            "videoAddress" : "/video",
            "audioFile" : "audioFile.wav",
            "arduinoDriver" : "USB\\VID_1A86&PID_7523"
        }
        # Serializing json
        json_object = json.dumps(data, indent=4)
 
        # Writing to config.json
        with open(settingsFile, "w") as outfile:
            outfile.write(json_object)
    return data

def killProcess(processName):
    try:
        subprocess.run(["taskkill", "/IM", processName, "/F"])
        #print(f"killed process")
    except:
        print("No process to Kill")

#----------End Functions------------------

#----------Start Main---------------------
# Get the current working
# directory (CWD)
try:
    this_file = __file__
except NameError:
    this_file = sys.argv[0]
this_file = os.path.abspath(this_file)
if getattr(sys, 'frozen', False):
    cwd = os.path.dirname(sys.executable)
    bundle_dir = sys._MEIPASS
else:
    cwd = os.path.dirname(this_file)
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

print("Current working directory:", cwd)

settingsFile = os.path.join(cwd, "config.json")
config = readConfig(settingsFile)
baudrate = config["baudrate"]
uart = config["uart"]
oscServer = config["oscServer"]
oscPort = config["oscPort"]
idleAddress = config["idleAddress"]
videoAddress = config["videoAddress"]
audioFile = config["audioFile"]
arduinoDriver = config["arduinoDriver"]

# Set up the OSC client
client = udp_client.SimpleUDPClient(oscServer, oscPort)

print("Setup Serial")

# setup Seiral
noSerial = True
while noSerial:
    try:
        if uart == "auto":
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if "USB" in p.description:
                    uart = p.device
        print(f"Using port: {uart}")
        
        ser = serial.Serial(
            port=uart,
            baudrate=baudrate,
            timeout=1
        )
        noSerial = False
    except serial.SerialException as e:
        #print("An exception occurred:", e)
        if "PermissionError" in str(e):
            print("PermissionError")
            print("Restart arduino driver")
            #arduinoDriver=r"USB\VID_1A86&PID_7523"
            print(f"Using driver: {arduinoDriver}")
            devconFile = os.path.join(bundle_dir, "devcon.exe")
            subprocess.run([devconFile, "disable", arduinoDriver])
            subprocess.run([devconFile, "enable", arduinoDriver])
        else:
            print("An unexpected serial error occurred.")
    except Exception as error:
        print("An unexpected error occurred:", error)

#Setup list to hold LED states
print("Play Audio")
audioPlayer = subprocess.Popen(["mpv", audioFile])
time.sleep(2)
killProcess("mpv.exe")
ledState = True
print("Ready")
try:
    while True:
        x=ser.readline().strip().decode()
        if x.isnumeric():
            xInt = int(x)
            killProcess("mpv.exe")
            audioPlayer = subprocess.Popen(["mpv", audioFile])
            client.send_message(videoAddress, 1)
            print("osc message sent and Audio Started")
            ledState = False
            time.sleep(2)
            
        if (audioPlayer.poll() is not None) and (not ledState):
            #Turn on Lights
            ledState = True
            client.send_message(idleAddress, 1)

except KeyboardInterrupt:
    ser.close()
