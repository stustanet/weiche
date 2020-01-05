#!/bin/bash

if [[ -z $1 ]]; then
    echo "$0 lolz.py [lolz2.py]"
    exit 1
fi

#IP=192.168.13.137
IP=192.168.0.105
PORT=/dev/ttyUSB0
WEBREPL=~/code/webrepl/webrepl_cli.py
ESPTOOL=/usr/bin/esptool.py
PW=thei1ahGh

for FILE in $@
do
    # copy file to esp
    $WEBREPL -p $PW $FILE $IP:$FILE
done

# "reset"
#$ESPTOOL --port $PORT run

# reconnect
#screen $PORT 115200,cs8,-parenb,-cstopb,-hupcl
