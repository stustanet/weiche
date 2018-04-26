from umqtt.simple import MQTTClient
from machine import Pin, unique_id, PWM
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

SERVER = "knecht.stusta.de"
TOPIC = b"space/led"


# Received messages from subscriptions will be delivered to this callback
def sub_cb(topic, msg):
    print((topic, msg))

    try:
        msg = msg.decode('utf-8')
        j = json.loads(msg)
    except Exception as e:
        print("json kapudd", e)
        return

    client_id = CLIENT_ID.decode('utf-8')
    if client_id in j.keys():
        for n in range(len(j[client_id])):
            pwm_val = int(j[client_id][n])
            led = PWM_PINS[n]
            print("dimming {} to {}".format(led, pwm_val))

            if pwm_val < 0:
                pwm_val = 0
            if pwm_val > 1023:
                pwm_val = 1023

            try:
                PWM_LEDS[n].duty(pwm_val)
            except Exception as e:
                print(e)


def main(server=SERVER):
    print(CLIENT_ID)
    for pin in PWM_PINS:
        led = Pin(pin, Pin.OUT)
        print(pin, led)
        PWM_LEDS.append(PWM(led))

    # set pwm freq, its global for all pins
    PWM(led).freq(1000)

    c = MQTTClient(CLIENT_ID, server)
    c.set_callback(sub_cb)
    c.connect()
    c.subscribe(TOPIC)
    while True:
        c.wait_msg()

    c.disconnect()


main()
