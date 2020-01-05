# Install micropython #

```
$ wget http://micropython.org/resources/firmware/esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
$ esptool.py --port /dev/ttyUSB0 erase_flash
$ esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
```

# Configure wifi #
```
$ screen /dev/ttyUSB0 115200,cs8,-parenb,-cstopb,-hupcl
```
Follow help() for wifi usage.

# Configure webrepl #
```
import webrepl_setup
```
Follow wizard.

# Deploy weiche #
```
./deploy.sh boot.py main.py weiche.py config.py artnet.py effects.py betterntp.py http_grab.py
```

# Run weiche #
Enter the seriel shell and run

```
import weiche
weiche.initial_setup()
```

to install the required upip stuff.

now the autostart should be possible
