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
#from pynput.keyboard import Key, Controller
from pythonosc import udp_client
import subprocess
import tinytuya #pip install tinytuya

#keyboard = Controller()

def readConfig(settingsFile):
    if os.path.isfile(settingsFile):
        with open(settingsFile) as json_file:
            data = json.load(json_file)
    else:
        data = {
            "uart" : "auto",
	        "baudrate" : 9600,
	        "keyPress" : "abcdefghijklmnopqrstuvwxyz",
            "numBtns" : 1,
            "useTimer" : 1,
            "timer" : 120,
            "oscServer" : "127.0.0.1",
            "oscPort" : 8010,
            "oscAddress" : "/serial",
            "audioFile" : "audioFile.wav",
            "arduinoDriver" : "USB\\VID_1A86&PID_7523",
            "switches" : [
                {
                    "dev_id": "eb2420aa05e3856413zj29",
                    "local_key" : "1.vptSfQ[.aF0Lv$"
                }, 
                {
                    "dev_id" : "ebf9459576dd538419ohwz",
                    "local_key" : "N[=Kb=+Uk)DW(>zT"
                }
            ]
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

def control_switches(state):
    if len(switch) > 0:
        for local_device in switch:
            #print(local_device)
            try:
                if state:
                    local_device.turn_on()
                    print("Switchs Turned on")
                else:
                    local_device.turn_off()
                    print("Switch Turned off")
            except:
                print("Error conecting to Switch")
                return False
    return state

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
keyPress = config["keyPress"]
oscServer = config["oscServer"]
oscPort = config["oscPort"]
oscAddress = config["oscAddress"]
switches = config["switches"]
audioFile = config["audioFile"]
arduinoDriver = config["arduinoDriver"]

print("Read Tuya Devices")
tuyaScan = tinytuya.deviceScan()

switch = list()
print("Setup Tuya Switches")
for device in tuyaScan.values():
    for i, local_device in enumerate(switches):
        if device["gwId"] == local_device["dev_id"]:
            switch.append(tinytuya.OutletDevice(dev_id=local_device["dev_id"],
                                address=device["ip"],
                                local_key=local_device["local_key"],
                                version=3.4))
            break

ledState = control_switches(True)

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

print("Ready")
try:
    while True:
        x=ser.readline().strip().decode()
        if x.isnumeric():
            xInt = int(x)
            killProcess("mpv.exe")
            ledState = control_switches(False)
            audioPlayer = subprocess.Popen(["mpv", audioFile])
            client.send_message(oscAddress, keyPress[xInt])
            print("osc message sent and Audio Started")
            time.sleep(2)
            
        if (audioPlayer.poll() is not None) and (not ledState):
            #Turn on Lights
            ledState = control_switches(True)    

except KeyboardInterrupt:
    ser.close()
