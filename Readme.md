# Install micropython #

```
$ wget http://micropython.org/resources/firmware/esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
$ esptool.py --port /dev/ttyUSB1 erase_flash
$ esptool.py --port /dev/ttyUSB1 --baud 460800 write_flash --flash_size=detect 0 esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
```

# Configure wifi #
```
$ screen /dev/ttyUSB1 115200,cs8,-parenb,-cstopb,-hupcl
```
Follow help() for wifi usage.

# Configure webrepl #
```
import webrepl_setup
```
Follow wizard.

# Initial Setup

    import upip
    upip.install('micropython-umqtt.simple')
    upip.install('json')


# Deploy weiche #
```
./deploy.sh weiche.py
```

# Run weiche #
Enter the seriel shell and run
```
import weiche
```
