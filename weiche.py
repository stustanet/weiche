#!/usr/bin/env python3.6
# python 3.6 is required for mqtt...

def initial_setup():
    import upip
    upip.install('micropython-umqtt.simple')
    upip.install('json')

try:
    # micropython boot
    from machine import Pin, unique_id, PWM
    import machine
    from umqtt.simple import MQTTClient
    import network
    import uselect as select

except ImportError:
    print("Switching to normal python boot mode")
    # normal python boot
    from unix_machine import Pin, unique_id, PWM
    import unix_machine as machine
    from unix_mqtt import MQTTClient
    import unix_network as network

    import select

import gc
import sys

import time
import json
import time
import gc
import sys


from artnet import ArtNetController
from betterntp import BetterNTP
from config import ConfigInterface
from effects import EffectQueue

"""
all GPIOs have no internal PULL-UPs

chip   | led channel
-------+---------------
GPIO4  |     0.0
GPIO5  |     0.1
GPIO12 |     1.0
GPIO13 |     1.1
GPIO14 |     2.0
GPIO15 |     2.1
GPIO0  |     3.0
GPIO2  |     3.1
"""

PWM_PINS = [4, 5, 12, 13, 14, 15, 0, 2]
PWM_LEDS  = []

statusled = Pin(16, Pin.OUT)

config = ConfigInterface()
ntp = BetterNTP()
effectqueue = EffectQueue(config, ntp, lambda x: set_lights(x) )

# Received messages from subscriptions will be delivered to this callback
def mqtt_cb(topic, msg):
    global config
    try:
        msg = msg.decode('utf-8')
        jsondata = json.loads(msg)
    except:
        print("[!] Json error: ", msg)

    if isinstance(topic, bytes):
        topic = topic.decode()

    if topic == config.config('mqtt', 'default_topic'):
        mqtt_light_callback(msg, jsondata)
    elif topic == config.config('mqtt', 'queue_topic'):
        mqtt_queue_callback(msg, jsondata)


def mqtt_light_callback(msg, jsondata):
    if config.client_id not in jsondata.keys():
        return
    background_lights = jsondata[config.client_id]

    while len(background_lights) < 8:
        background_lights.append(0)

    set_lights(jsondata[config.client_id])


def mqtt_queue_callback(msg, jsondata):
    global effectqueue
    if not isinstance(jsondata, dict):
        print("[!] cue data has to be {\"ID\":[[time,[led1, led2, ...]], ...]")
        return
    if config.client_id not in jsondata.keys():
        print("[!] Not meant for me")
        return

    print("[*] Received queue update. New cue:")
    effectqueue.update(jsondata[config.client_id])
    effectqueue.debug()


def set_lights(light_vals):
    if light_vals is None:
        light_vals = []


    print("[*] Setting leds to", light_vals)
    for n, (pwm_val, led) in enumerate(zip(light_vals, PWM_LEDS)):
        pwm_val = int(pwm_val)
        if pwm_val < 0:
            pwm_val = 0
        if pwm_val > 1023:
            pwm_val = 1023

        #print("[*] dimming led {} to {}".format(n, pwm_val))

        try:
            led.duty(pwm_val)
        except Exception as e:
            raise e
            print(e)


uartBuffer = ''
def uart_receive():
    global uartBuffer
    c = sys.stdin.read(1)
    if c in "\n\r":
        command = uartBuffer.strip()
        uartBuffer = ''
        handle_uart_cmd(command)
    else:
        uartBuffer += c
    return True

def handle_uart_cmd(cmd):
    parts = cmd.split()
    if len(parts) < 2 or len(parts) > 8 or parts[0] != 'SET':
        print("Expected SET <VALUE0> ... <VALUE7>")
        print("Press Ctrl-C to exit to a python shell.")
        return

    for i in range(0, len(parts) - 1):
        val = None
        if parts[i + 1].isdigit():
            val = int(parts[i + 1])

        if val is None or val < 0 or val > 1023:
            print("Expected an integer between 0 and 1023 but got \"{}\"".format(parts[i + 1]))
            continue

        print("[*] set led {} to {} by serial request".format(i, val))
        PWM_LEDS[i].duty(val)


def artnet_update(data):
    """
    Set the light to data, data is in the range of 0-255
    """
    set_lights([v * 4 for v in data])

    return True

def main():
    global config, effectqueue
    system_is_sane = True

    print("[*] weiche {} startet.".format(config.client_id))
    for pin in PWM_PINS:
        led = Pin(pin, Pin.OUT)
        PWM_LEDS.append(PWM(led))

    statusled.on()

    # set pwm freq, its global for all pins
    PWM(led).freq(1000)

    print("[*] Enabling default mood")
    # config.default_config will read from the stored config - asap
    set_lights(config.default_config('idle', 'lights', []))

    sta_if = network.WLAN(network.STA_IF)

    while not sta_if.isconnected():
        print('[?] Waiting for network connection...')
        time.sleep(0.5)
        statusled.off()
        time.sleep(0.5)
        statusled.on()

    # Network is available
    print("[*] IP address: ", sta_if.ifconfig()[0])

    possible_controllers = ["192.168.0.102", "192.168.13.37", ]
    gateway = sta_if.ifconfig()
    if gateway \
       and len(gateway) > 3 \
       and gateway[3] \
       and gateway[3] not in possible_controllers:
        possible_controllers.append(gateway[3])
    #possible_controllers.append("mqttcontrol.hackerspace.stusta.de")

    last_ntp_update = 0
    while True:
        # network is available, dropping out of here recreates network context
        print("[?] Starting setup")

        try:
            statusled.off()

            if not config.ready():
                print("[*] Collecting config")
                if not config.getconfig(possible_controllers):
                    print("[!] Could not get config. retrying")
                    continue;

            poll = select.poll()
            ntp.set_host(config.config('ntp', 'host'))

            # uart is always enabled!
            uartBuffer = ''
            print("[*] Enabling UART control")
            poll.register(sys.stdin, select.POLLIN)

            artnet = None
            if config.config('artnet', 'enabled'):
                print("[*] Connecting to Art-Net")
                artnet = ArtNetController(artnet_update)
                artnet.setconfig(config)
                artnet.init_broadcast_receiver()
                poll.register(artnet.socket, select.POLLIN)
            else:
                print("[*] ArtNet disabled")

            mqtt = None
            if config.config('mqtt', 'enabled'):
                server = config.config('mqtt', 'server')
                server, port = server.split(":", 1)
                print("[*] Connecting to mqtt at %s port %s"%(server, port))
                mqtt = MQTTClient(config.CLIENT_ID, server)
                mqtt.set_callback(mqtt_cb)
                mqtt.connect()
                poll.register(mqtt.sock, select.POLLIN)

                default_topic = config.config('mqtt', 'default_topic')
                print("[*] Subscribing to topic (single msg)", default_topic)
                mqtt.subscribe(default_topic)

                cue_topic = config.config('mqtt', 'queue_topic')
                print("[*] Subscribing to topic (cue)", cue_topic)
                mqtt.subscribe(cue_topic)
                def system_is_not_sane(self):
                    system_is_sane = False
                mqtt.on_disconnect = system_is_not_sane

                # Request an update for the current light state
                mqtt.publish(b"/haspa/power/status", json.dumps([config.client_id]))
            else:
                print("[*] mqtt disabled")

            print("[*] Ready for messages")

            system_is_sane = True
            while system_is_sane:
                # Update the LED 1/min
                if not effectqueue.active() \
                   and (ntp.nowfloat() - last_ntp_update) > 60:
                    ntp.update()
                    last_ntp_update = ntp.nowfloat()

                # if effectqueue is having data speed up the main loop
                ready = []
                if effectqueue.active():
                    while effectqueue.active() and not ready:
                        effectqueue.trigger()
                        ready = poll.poll(10)
                else:
                    # effectqueue inactive
                    gc.collect()
                    ready = poll.poll(250)

                # if the poll() returned an empty list, we are sad
                if not ready:
                    statusled.off()
                    continue

                statusled.on()
                err = False
                #print("Ready socks:", ready)
                for sock, typ in ready:
                    if typ != select.POLLIN:
                        # uselect says:
                        # Note that flags uselect.POLLHUP and uselect.POLLERR
                        # can be returned at any time, and must be acted on
                        # accordingly
                        #
                        # We react by recreating all sockets.
                        err = True
                        print("[!] Socket ", sock, "reported POLLUP or POLLERR, therefore bye")
                        break
                    sock
                    if artnet and sock == artnet.socket:
                        print("[*] Artnet received")
                        if not artnet.run_once():
                            break

                    elif mqtt and sock == mqtt.sock:
                        print("[*] MQTT received")
                        if not mqtt.check_msg():
                            break

                    elif sock == sys.stdin or sock == 0:
                        if not uart_receive():
                            break
                    else:
                        print("Unknown received: ", sock)

                    gc.collect()
                if err:
                    break
            print("[!] connection loop terminated. reinitializing")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            #raise e # For debug times
            print("Error was: ", e)
            sys.print_exception(e)
            print("Sleeping for 10 seconds")

            time.sleep(10)
            machine.reset()

if __name__=="__main__":
    main()
