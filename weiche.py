from umqtt.simple import MQTTClient
from machine import Pin, unique_id, PWM
import network
import ubinascii
import json

"""
all GPIOs have no internal PULL-UPs

board  | chip   | led channel
-------+--------+---------------
D1     | GPIO5  |     0
D2     | GPIO4  |     1
D5     | GPIO14 |     2
D6     | GPIO12 |     3
"""

PWM_PINS = [5, 4, 14, 12]
PWM_LEDS  = []

CLIENT_ID = ubinascii.hexlify(unique_id())
client_id = CLIENT_ID.decode('utf-8')

SERVER = "192.168.13.37"
TOPIC = b"/haspa/led"


# Received messages from subscriptions will be delivered to this callback
def sub_cb(topic, msg):
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

            try:
                led.duty(pwm_val)
            except Exception as e:
                print(e)



def main(server=SERVER):
    print("[*] weiche {} startet.".format(client_id))
    for pin in PWM_PINS:
        led = Pin(pin, Pin.OUT)
        PWM_LEDS.append(PWM(led))

    # set pwm freq, its global for all pins
    PWM(led).freq(1000)

    for p in PWM_LEDS:
        p.duty(512)

    sta_if = network.WLAN(network.STA_IF)
    while not sta_if.isconnected():
        print('Waiting for network connection...')
        time.sleep(1)

    c = MQTTClient(CLIENT_ID, server)
    c.set_callback(sub_cb)
    c.connect()
    c.subscribe(TOPIC)
    while True:
        c.wait_msg()

    c.disconnect()


main()
