from umqtt.simple import MQTTClient
from machine import Pin, unique_id, PWM
import machine
import network
import ubinascii
import json
import time
import gc
import sys


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

CLIENT_ID = ubinascii.hexlify(unique_id())
client_id = CLIENT_ID.decode('utf-8')

SERVER = "192.168.13.37"
TOPIC = b"/haspa/led"

valuesFromMqtt = False


# Received messages from subscriptions will be delivered to this callback
def sub_cb(topic, msg):
    global a, valuesFromMqtt
    try:
        msg = msg.decode('utf-8')
        j = json.loads(msg)
    except Exception as e:
        print("[!] json kapudd", e)
        return

    if client_id in j.keys():
        # <3 python
        for n, (pwm_val, led) in enumerate(zip(j[client_id], PWM_LEDS)):
            pwm_val = int(pwm_val)

            if pwm_val < 0:
                pwm_val = 0
            if pwm_val > 1023:
                pwm_val = 1023

            print("[*] dimming led {} to {}".format(n, pwm_val))

            valuesFromMqtt = True

            try:
                led.duty(pwm_val)
            except Exception as e:
                print(e)

def handle_uart_cmd(cmd):
    global valuesFromMqtt
    parts = cmd.split()
    if len(parts) < 2 or len(parts) > 8 or parts[0] != b'SET':
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


        valuesFromMqtt = False
        print("[*] set led {} to {} by serial request".format(i, val))
        PWM_LEDS[i].duty(val)


def main(server=SERVER):
    print("[*] waiting 0.5 seconds for good measure.".format(client_id))
    print("[*] weiche {} startet.".format(client_id))
    for pin in PWM_PINS:
        led = Pin(pin, Pin.OUT)
        PWM_LEDS.append(PWM(led))

    statusled.on()

    # set pwm freq, its global for all pins
    PWM(led).freq(1000)

    for i, p in enumerate(PWM_LEDS):
        if (i % 2) == 1:
            p.duty(512)
        else:
            p.duty(0)


    sta_if = network.WLAN(network.STA_IF)
    while not sta_if.isconnected():
        print('[?] Waiting for network connection...')
        time.sleep(0.5)
        statusled.off()
        time.sleep(0.5)
        statusled.on()

    print('[*] We have network')
    c = MQTTClient(CLIENT_ID, server)
    c.set_callback(sub_cb)
    print("[*] connecting to mqtt")
    c.connect()
    print("[*] connected")
    c.subscribe(TOPIC)

    c.publish(b"/haspa/power/status", b"{}")

    statusled.off()
    print("[*] Ready for messages")

    print("[*] Initialize UART for control commands")

    ver = sys.implementation[1]
    if ver[0] > 1 or ver[1] > 9:
        print("[!] The UART only works on versions <= 1.9.x, but got version", ver)

    time.sleep(1)
    u = machine.UART(0, 115200)

    uartBuffer = b''

    print ("IP address: ", sta_if.ifconfig()[0])

    while True:
        c.check_msg()

        d = u.read()
        if d is not None:
            uartBuffer += d
            nl = uartBuffer.find(b'\r')
            if nl >= 0:
                command = uartBuffer[:nl].strip()
                uartBuffer = uartBuffer[(nl + 1):]
                handle_uart_cmd(command)

        if valuesFromMqtt:
            statusled.on()
        else:
            statusled.off()

        gc.collect()

    c.disconnect()


main()
