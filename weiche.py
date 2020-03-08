#!/usr/bin/env python3.6
# python 3.6 is required for mqtt...

#pylint: disable=bare-except,broad-except
"""
Die weiche weicht zum Hauptbahnhof.

Weiche implements the local controls for a hackerspace light control interface
"""

import gc

print("GC start", gc.mem_free())

gc.collect()

try:
    # micropython boot
    import machine
    from umqtt.simple import MQTTClient
    import network
    import uselect as select

except ImportError:
    print("Switching to normal python boot mode")
    # normal python boot
    import unix_machine as machine
    from unix_mqtt import MQTTClient
    import unix_network as network

    import select

import sys
import time
import ujson as json

gc.collect()

from config import ConfigInterface

gc.collect()


# all GPIOs have no internal PULL-UPs
#
# chip   | led channel
# -------+---------------
# GPIO4  |     0.0
# GPIO5  |     0.1
# GPIO12 |     1.0
# GPIO13 |     1.1
# GPIO14 |     2.0
# GPIO15 |     2.1
# GPIO0  |     3.0
# GPIO2  |     3.1
PWM_PINS = [4, 5, 12, 13, 14, 15, 0, 2]

print("GC After imports", gc.mem_free())

class WeicheMqtt:
    """
    MQTT Interface for all the weiche logic
    """

    def __init__(self, config, set_lights):
        self.config = config
        self.set_lights = set_lights
        self.mqtt = None

    def connect(self):
        """
        Connect to the configured mqtt server, subscribe to topics and request
        an update
        """
        server = self.config.config('mqtt', 'server')
        server, port = server.split(":", 1)
        print("[*] Connecting to mqtt at %s port %s"%(server, port))
        self.mqtt = MQTTClient(self.config.client_id, server)
        self.mqtt.set_callback(self.mqtt_cb)
        self.mqtt.connect()

        default_topic = self.config.config('mqtt', 'default_topic')
        print("[*] Subscribing to topic (single msg)", default_topic)
        self.mqtt.subscribe(default_topic)

        mood_topic = self.config.config('mqtt', 'mood_topic')
        if mood_topic is None:
            print("[!] no mood topic set, ignoring")
        else:
            print("[*] Subscribing to topic (mood msg)", mood_topic)
            self.mqtt.subscribe(mood_topic)

        # Request an update for the current light state
        self.mqtt.publish(b"/haspa/power/status",
                          json.dumps([self.config.client_id]))

        return self.mqtt.sock

    # Received messages from subscriptions will be delivered to this callback
    def mqtt_cb(self, topic, msg):
        """
        Branching for the different topics
        """
        try:
            msg = msg.decode('utf-8')
            jsondata = json.loads(msg)
        except:
            print("[!] Json error: ", msg)

        if isinstance(topic, bytes):
            topic = topic.decode()

        if topic == self.config.config('mqtt', 'default_topic'):
            self.mqtt_light_callback(jsondata)
        elif topic == self.config.config('mqtt', 'mood_topic'):
            self.mqtt_mood_callback(jsondata)


    def mqtt_light_callback(self, jsondata):
        """
        Simple set lights targeted for this controller
        """
        if self.config.client_id not in jsondata.keys():
            return
        background_lights = jsondata[self.config.client_id]

        while len(background_lights) < 8:
            background_lights.append(0)

        self.set_lights(background_lights)

    def mqtt_mood_callback(self, jsondata):
        """
        Simple set lights, does not contain a target id
        """
        background_lights = jsondata

        if len(background_lights) == 4:
            # double it up
            background_lights += background_lights

        while len(background_lights) < 8:
            background_lights.append(0)

        self.set_lights(background_lights)


    @property
    def sock(self):
        """ Get the mqtt socket for poll() or select() """
        return self.mqtt.sock

    def check_msg(self):
        """ Proxy """
        return self.mqtt.check_msg()


class Weiche:
    #Main Orchestrator for the local weiche behaviour

    def __init__(self):
        self.statusled = machine.Pin(16, machine.Pin.OUT)
        self.config = ConfigInterface()
        self.poll = select.poll()
        self.leds = []

        self.mqttinterface = None

        self.running = True

        print("[*] weiche {} startet.".format(self.config.client_id))
        for pin in PWM_PINS:
            led = machine.Pin(pin, machine.Pin.OUT)
            self.leds.append(machine.PWM(led))

        self.statusled.on()

        # set pwm freq, its global for all pins
        machine.PWM(led).freq(1000)

        print("[*] Enabling default mood")
        # config.default_config will read from the stored config - asap
        self.set_lights(self.config.default_config('idle', 'lights', []))

        print("GC After boot", gc.mem_free())

    def set_lights(self, light_vals):
        #Set light values for all leds
        if light_vals is None:
            light_vals = []

        print("[*] Setting leds to", light_vals)
        for pwm_val, led in zip(light_vals, self.leds):
            pwm_val = int(pwm_val)
            if pwm_val < 0:
                pwm_val = 0
            if pwm_val > 1023:
                pwm_val = 1023
            led.duty(pwm_val)


    uartbuffer = ''
    def uart_receive(self):
        #Read a single byte from stdin and process it maybe as a command
        char = sys.stdin.read(1)
        if char in "\n\r":
            command = self.uartbuffer.strip()
            self.uartbuffer = ''
            self.handle_uart_cmd(command)
        else:
            self.uartbuffer += char
        return True

    def handle_uart_cmd(self, cmd):
        #Handle the setting of LED values
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
            self.leds[i].duty(val)


    def init(self):
        gc.collect()
        #Setup basic stuff for the server - to be done only once

        sta_if = network.WLAN(network.STA_IF)

        while not sta_if.isconnected():
            print('[?] Waiting for network connection...')
            time.sleep(0.1)
            self.statusled.off()
            time.sleep(0.1)
            self.statusled.on()

        # Network is available
        print("[*] IP address: ", sta_if.ifconfig()[0])

        #possible_controllers.append("mqttcontrol.hackerspace.stusta.de")
        #possible_controllers = ["192.168.0.102", "192.168.13.37", ]
        possible_controllers = ["192.168.13.37", ]
        gateway = sta_if.ifconfig()
        if gateway \
           and len(gateway) > 3 \
           and gateway[3] \
           and gateway[3] not in possible_controllers:
            possible_controllers.append(gateway[3])

        self.statusled.on()
        if not self.config.ready():
            print("[*] Collecting config")
            if not self.config.getconfig(possible_controllers):
                print("[!] Could not get config. retrying")
                raise RuntimeError("Could not get config")

        self.statusled.off()

        gc.collect()

    def connect(self):
        #Connect to all interfaces configured in the config

        # uart is always enabled!
        print("[*] Enabling UART control")
        self.poll.register(sys.stdin, select.POLLIN)

        if self.config.config('mqtt', 'enabled'):
            self.mqttinterface = WeicheMqtt(self.config,
                                            self.set_lights)
            sock = self.mqttinterface.connect()
            self.poll.register(sock, select.POLLIN)
        else:
            self.mqttinterface = None
            print("[*] mqtt disabled")

    def run(self):
        gc.collect()
        #Main loop of the weiche. Will terminate as soon as something bad
        #happened, that requires a reconnect.
        #when raising an exception it requires the reset of the controller
        self.running = True
        while self.running:
            gc.collect()
            ready = self.poll.poll(250)

            # if the poll() returned an empty list, we are sad
            if not ready:
                self.statusled.off()
                continue

            self.statusled.on()
            for sock, typ in ready:
                if typ != select.POLLIN:
                    # uselect says:
                    # Note that flags uselect.POLLHUP and uselect.POLLERR can
                    # be returned at any time, and must be acted on accordingly
                    #
                    # We react by recreating all sockets.
                    self.running = False
                    print("[!] Socket ", sock, "reported POLLUP or POLLERR, "
                          "therefore shutting down")
                    break

                elif self.mqttinterface and sock == self.mqttinterface.sock:
                    print("[*] MQTT received")
                    self.mqttinterface.check_msg()

                elif sock in [sys.stdin, 0]:
                    # sock == 0 is required on linux
                    self.uart_receive()
                else:
                    print("Unknown socket: ", sock)

                gc.collect()

    def main(self):
        #
        #Start the weiche, connect it to all interfaces and run it
        #
        #When an exception is raised, this method will wait for 10 seconds
        #in order for an Ctrl+C debugger occur.
        self.init()

        while True:
            # network is available, dropping out of here recreates network context
            print("[?] Starting setup")
            try:
                self.connect()
                gc.collect()
                print("[*] Ready for messages")
                self.run()
                gc.collect()
                print("[!] connection loop terminated. reinitializing")
            except KeyboardInterrupt: #pylint: disable=try-except-raise
                # filter out and allow keyboard interrupts
                raise
            except Exception as exc:
                #raise e # For debug times
                sys.print_exception(exc)
                print("Sleeping for 10 seconds")
                time.sleep(10)
                machine.reset()


weiche = Weiche()

def main():
    """ - """
    weiche.main()

if __name__ == "__main__":
    main()
