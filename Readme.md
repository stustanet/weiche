# Setup
## Install micropython

```
$ wget http://micropython.org/resources/firmware/esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
$ esptool.py --port /dev/ttyUSB1 erase_flash
$ esptool.py --port /dev/ttyUSB1 --baud 460800 write_flash --flash_size=detect 0 esp8266-20180421-v1.9.3-552-gb5ee3b2f.bin
```

## Configure wifi
```
$ screen /dev/ttyUSB1 115200,cs8,-parenb,-cstopb,-hupcl
```
Follow help() for wifi usage.

## Configure webrepl
```
import webrepl_setup
```
Follow wizard.

## Initial Setup

    import upip
    upip.install('micropython-umqtt.simple')
    upip.install('json')


## Deploy weiche
```
./deploy.sh weiche.py
```

## Run weiche
Enter the seriel shell and run
```
import weiche
```


# Configuration

To configure the controllers provide a webserver reachable within the network of
the nodes either on the ip `192.168.13.37` or on the default gateway handed out
by your dhcp server on ports 8000 or 80.

All these options will be tried by a booting weiche. If no config is found, the last
valid config will be used. If no valid config exists, the system will continue to reboot,
until you provide a config.

The config file looks like this:

```
{
        "246f28248b30": {
                "idle": {
                        "lights": [0, 512, 0, 512, 0, 512, 0, 512]
                },
                "mqtt": {
                        "enabled": 1,
                        "server": "192.168.0.102:1883",
                        "default_topic": "/haspa/led/test",
                        "queue_topic": "/haspa/led/cue",
                        "mood_topic": "/haspa/mood/main",
                        ۰"max_cue_future_seconds": 120
                },
                "artnet": {
                        "enabled": 1,
                        "universe": 1,
                        "start_address": 0
                },
                "serial": {},
                "ntp": {
                        "host": "pool.ntp.org"
                }
        },
...
}
```

`246f28248b30` is the unique_id of a weiche, either printed on it or it is echoed
on startup. It is also sent on bootup to the topic `/haspa/power/status`.

`idle:lights`: an array of up to 8 channels that define the color the node should
have before it receives its first color message or if mqtt is down.

`mqtt:enabled`: should mqtt be used.

`mqtt:server`: which server should the mqtt client use. use `:` to note the port.
The weiche systems do not support encrypted mqtt.

`mqtt:default_topic`: the individual addressed light topic to use. (see below)

`mqtt:mood_topic`: the global light topic to use. (see below)

`mqtt:queue_topic`: the individual addressed light show to use. (see below)

`max_cue_future_seconds`: the maximum length into the future a cue is allowed.
Longer cues than this value have to be split into multiple messages.

`artnet:enabled`: should artnet be used

`artnet:universe`: on which artnet universe is the node

`artnet:start_address`: which dmx address within that universe does this node have

`ntp:host`: which ntp host to use - this has to be reachable in order for the lightshows to work
Best set up one in your own network on the same host as the mqtt server.

# Topics

Each topic message will override previous messages.

## default_topic (/haspa/led/<room>)

individually addressed light values, together for all nodes within this packet.

A message to set the lights of one controller to a specific value looks like that (leds not described here will be turned off)

```
{
    "246f28248b30": [0, 1023, 0, 1023]
}
```

## mood_topic (/haspa/mood/<room>)

all leds of the domain should have this color. An example message to set the hackerspace to warm white:

```
[0. 300, 0, 300, 0, 300, 0, 300]
```

## queue_topic (/haspa/cue)

Set a light show for each controller individually.

A light show is based on timestamps in milliseconds since 2000-01-01T00:00:00.0000.
When a new light show arrives, all previous elements that would have occured after
the first element in the new show are dropped.
Also all elements in the past are dropped.

If you send an empty show, the full show is dropped and the default mood is applied
again.

The elements have to be sorted as earliest segment first.

an example message for having a 1 second blinking show between warm and cold white:

```
{
    "246f28248b30":[
        [6123234534, [0, 1023, 0, 1023]],
        [6123235534, [1023, 0, 1023, 0]],
        [6123236534, [0, 1023, 0, 1023]],
        [6123237534, [1023, 0, 1023, 0]],
    ]
    ...
}
```
