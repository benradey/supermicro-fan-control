#!/usr/bin/python

import os
import time
import sys
import subprocess
import datetime
import time

MIN_FAN = 25
MAX_FAN = 100
DEBOUNCE_LENGTH = 20
SLEEP_TIME = 1
HDD_TEMP_QUERY_PERIOD = 180

thresholdMap = dict({
    'CPU1': [50, 80],
    'CPU2': [50, 80],
    'System': [50, 72],
    'Peripheral': [60, 72],
    'MB_10G': [77, 88],
    'MB/AOM_SAS': [65, 88],
    '/dev/sda': [39, 50],
    '/dev/sdb': [39, 50],
    '/dev/sdc': [39, 50],
    '/dev/sdd': [39, 50],
    '/dev/sde': [39, 50],
    '/dev/sdf': [39, 50],
    '/dev/sdg': [39, 50],
    '/dev/sdh': [39, 50],
    '/dev/sdi': [39, 50],
    '/dev/sdj': [39, 50],
    '/dev/sdk': [39, 50],
    '/dev/sdl': [39, 50],
    '/dev/sdm': [39, 50]
})

IPMI_COMMAND_PREFIX = 'ipmitool -H 192.168.1.160 -U ADMIN -f /root/ipmiPassword -I lanplus '
IPMI_SENSOR_COMMAND = IPMI_COMMAND_PREFIX + 'sensor'
IPMI_FAN_COMMAND_PREFIX = IPMI_COMMAND_PREFIX + 'raw 0x30 0x70 0x66 0x01 '
IPMI_FALLBACK_COMMAND_PREFIX = 'ipmitool '
IPMI_FALLBACK_SENSOR_COMMAND = IPMI_FALLBACK_COMMAND_PREFIX + 'sensor'
IPMI_FALLBACK_FAN_COMMAND_PREFIX = IPMI_FALLBACK_COMMAND_PREFIX + 'raw 0x30 0x70 0x66 0x01 '

debounceArray = [-1] * DEBOUNCE_LENGTH
debounceIndex = 0
previousSpeed = -1
quiet = len(sys.argv) > 1 and sys.argv[1] == 'quiet'
if quiet:
    print('Running in service mode.', flush=True)

def qprint(string):
    if not quiet:
        print(string)


def parseIpmiSensorOutput(stream, readings):
    for line in stream.readlines():
        if not 'degrees' in line:
            continue
        arr = line.split()
        name = arr[0]
        temp = float(arr[3])
        limit = float(arr[16])
        readings[name] = temp


qprint(thresholdMap)
lastHddQuery = time.time() - (60 * 60 * 24) # Pretend our last HDD read was 24h ago
readings = dict()

while True:
    stream = os.popen(IPMI_SENSOR_COMMAND)
    maxSetspeed = -1
    hottestDevice = ['', -1]
    parseIpmiSensorOutput(stream, readings)
    if 'CPU1' not in readings:
        print('Warning: using fallback IPMI sensor command', flush=True)
        stream = os.popen(IPMI_FALLBACK_SENSOR_COMMAND)
        parseIpmiSensorOutput(stream, readings)
    if time.time() - lastHddQuery > HDD_TEMP_QUERY_PERIOD:
        qprint(str(datetime.datetime.now()) + ' - Querying hddtemp')
        stream = os.popen('hddtemp')
        lastHddQuery = time.time()
        for line in stream.readlines():
            arr = line.split()
            name = arr[0][:-1]
            temp = float(arr[len(arr) - 1][:-2])
            readings[name] = temp
    qprint(readings)
    for name in thresholdMap:
        temp = readings[name]
        lowTemp = thresholdMap[name][0]
        highTemp = thresholdMap[name][1]
        setspeed = MAX_FAN
        if temp < lowTemp:
            setspeed = MIN_FAN
        elif temp < highTemp:
            setspeed = float((temp - lowTemp) / (highTemp - lowTemp) * 100)
            setspeed = setspeed + (MIN_FAN * (100 - setspeed) / 100) 
        setspeed = int(setspeed)
        qprint(name + ': ' + str(temp) + ' :: ' + str(lowTemp) + '-' + str(highTemp) + ' :: setspeed: ' + str(setspeed))
        if setspeed > maxSetspeed:
            hottestDevice = [name, temp]
        maxSetspeed = max(maxSetspeed, setspeed)
    if maxSetspeed > previousSpeed:
        print('New setspeed: ' + str(maxSetspeed) + ' due to ' + hottestDevice[0] + ': ' + str(hottestDevice[1]), flush=True)
    debounceArray[debounceIndex] = maxSetspeed
    debounceIndex += 1
    if debounceIndex >= DEBOUNCE_LENGTH:
        debounceIndex = 0
    qprint('debounceArray:')
    qprint(debounceArray)
    debouncedSpeed = -1
    for speed in debounceArray:
        debouncedSpeed = max(speed, debouncedSpeed)
    qprint('Debounced setspeed: ' + str(debouncedSpeed))

    if previousSpeed != debouncedSpeed:
        command = IPMI_FAN_COMMAND_PREFIX + '0 ' + str(debouncedSpeed)
        qprint(command)
        result = subprocess.run(command.split(), stdout=subprocess.DEVNULL)
        if result.returncode != 0:
            print('Warning: using fallback IPMI fan command', flush=True)
            subprocess.run((IPMI_FALLBACK_FAN_COMMAND_PREFIX + '0 ' + str(debouncedSpeed)).split())
        command = IPMI_FAN_COMMAND_PREFIX + '1 ' + str(debouncedSpeed)
        qprint(command)
        result = subprocess.run(command.split(), stdout=subprocess.DEVNULL)
        if result.returncode != 0:
            print('Warning: using fallback IPMI fan command', flush=True)
            subprocess.run((IPMI_FALLBACK_FAN_COMMAND_PREFIX + '1 ' + str(debouncedSpeed)).split())
    if debouncedSpeed == MIN_FAN and debouncedSpeed != previousSpeed:
        print('Reset fan speed to minimum (' + str(debouncedSpeed) + ')', flush=True)
    previousSpeed = debouncedSpeed
    time.sleep(SLEEP_TIME)

