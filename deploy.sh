#!/bin/bash

if [[ -z $1 ]]; then
    echo "$0 [lolz.py]}"
    exit 1
fi

FILE=$1
IP=192.168.88.250
PORT=/dev/ttyUSB1
WEBREPL=~/devel/python/micropython/webrepl/webrepl_cli.py
ESPTOOL=/usr/bin/esptool.py
PW=thei1ahGh

# copy file to esp
$WEBREPL -p $PW $FILE $IP:$FILE

# "reset"
$ESPTOOL --port $PORT run

# reconnect
screen $PORT 115200,cs8,-parenb,-cstopb,-hupcl
