from umqtt.simple import MQTTClient
from machine import Pin, unique_id, PWM
import network
import ubinascii
import json
import time
import gc


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


# Received messages from subscriptions will be delivered to this callback
def sub_cb(topic, msg):
    global a
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
    while True:
        statusled.on()
        c.wait_msg()
        statusled.off()
        gc.collect()

    c.disconnect()


main()
