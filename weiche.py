from umqtt.simple import MQTTClient
from machine import Pin, unique_id, PWM
import ubinascii
import json

PWM_PINS = [2, 12, 13, 14]
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
            #print("dimming {} to {}".format(led, pwm_val))

            try:
                PWM_LEDS[n].duty(1000 - pwm_val)
            except:
                pass


def main(server=SERVER):
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
