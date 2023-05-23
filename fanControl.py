#!/usr/bin/python

import os
import time

MIN_FAN = 17
MAX_FAN = 100

CPU_LOW = 50
CPU_HIGH = 80
thresholdMap = dict({
    'CPU1': [50, 80],
    'CPU2': [50, 80],
    'System': [45, 72],
    'Peripheral': [45, 72],
    'MB_10G': [75, 88],
    'MB/AOM_SAS': [65, 88]
})

IPMI_COMMAND_PREFIX = 'ipmitool -H 192.168.1.160 -U ADMIN -f /root/ipmiPassword -I lanplus '
IPMI_SENSOR_COMMAND = IPMI_COMMAND_PREFIX + 'sensor'
IPMI_FAN_COMMAND_PREFIX = IPMI_COMMAND_PREFIX + 'raw 0x30 0x70 0x66 0x01 '

print(thresholdMap)

while True:
    stream = os.popen(IPMI_SENSOR_COMMAND)
    readings = dict()
    maxSetspeed = -1
    hottestDevice = ['', -1]
    for line in stream.readlines():
        if not 'degrees' in line:
            continue
        arr = line.split()
        name = arr[0]
        temp = float(arr[3])
        limit = float(arr[16])
        readings[name] = temp
    print(readings)
    for name in thresholdMap:
        temp = readings[name]
        lowTemp = thresholdMap[name][0]
        highTemp = thresholdMap[name][1]
        setspeed = MAX_FAN
        print(name + ': ' + str(temp) + ' :: ' + str(lowTemp) + '-' + str(highTemp))
        if temp < lowTemp:
#            print('Temp below CPU_LOW')
            setspeed = MIN_FAN
        elif temp < highTemp:
            setspeed = float((temp - lowTemp) / (highTemp - lowTemp) * 100)
            setspeed = setspeed + (20 * (100 - setspeed) / 100) 
#            print('setspeed: ' + str(setspeed))
        setspeed = int(setspeed)
        print(name + ' setspeed: ' + str(setspeed))
        if setspeed > maxSetspeed:
            hottestDevice = [name, temp]
        maxSetspeed = max(maxSetspeed, setspeed)
    print('Final setspeed: ' + str(maxSetspeed) + ' due to ' + hottestDevice[0] + ': ' + str(hottestDevice[1]))
    command = IPMI_FAN_COMMAND_PREFIX + '0 ' + str(maxSetspeed)
    print(command)
    os.system(command)
    command = IPMI_FAN_COMMAND_PREFIX + '1 ' + str(maxSetspeed)
    print(command)
    os.system(command)
    time.sleep(2)

