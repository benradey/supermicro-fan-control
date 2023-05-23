#!/usr/bin/python

import os
import time

MIN_FAN = 17
MAX_FAN = 100

CPU_LOW = 50
CPU_HIGH = 80

IPMI_COMMAND_PREFIX = 'ipmitool raw 0x30 0x70 0x66 0x01 '

while True:
    stream = os.popen('ipmitool sensor')
    for line in stream.readlines():
        if 'degrees C' in line and 'CPU2' in line:
            #        print(line)
            arr = line.split()
            name = arr[0]
            temp = float(arr[3])
            limit = float(arr[16])
            setspeed = MAX_FAN
            print(name + ' ' + str(temp) + '/' + str(limit))
            if temp < CPU_LOW:
                print('Temp below CPU_LOW')
                setspeed = MIN_FAN
            elif temp < CPU_HIGH:
                setspeed = float((temp - CPU_LOW) / (CPU_HIGH - CPU_LOW) * 100)
                setspeed = setspeed + (20 * (100 - setspeed) / 100) 
                print('setspeed: ' + str(setspeed))
            command = IPMI_COMMAND_PREFIX + '0 ' + str(int(setspeed))
            print(command)
            os.system(command)
            command = IPMI_COMMAND_PREFIX + '1 ' + str(int(setspeed))
            print(command)
            os.system(command)
    time.sleep(2)

