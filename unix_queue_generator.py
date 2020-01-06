#!/usr/bin/env python3

import time
import json
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

TOPIC="/haspa/led/cue"

#HOST="knecht.stusta.de"
#ESPID="ee672600"

#HOST="localhost"
#ESPID="4242"

HOST="localhost"
ESPID="246f28248b30"

def send_mqtt(topic, message):
    publish.single(topic, message, hostname=HOST)

class Cue:
    cue = []
    last_element_offset = 0

    offset = 3600 # WINTER TIME!!
    #offset = 0

    def __init__(self):
        t = time.struct_time((2000, 1, 1,
                              0, 0, 0,
                              -1, -1, -1))
        # wday, yday, isdst is ignored
        self.esp_diff = 946684800# - 14 * 60 * 60 #time.mktime(t)

    def espnow(self):
        return time.time() - self.esp_diff

    def append(self, element, duration):
        if self.last_element_offset == 0:
            self.last_element_offset = self.espnow()

        self.cue.append([
            int((self.last_element_offset + self.offset) * 1000),
            element])
        self.last_element_offset += duration

    def render(self):
        self.append([0], 0)
        #print("ESP DIFF: ", self.esp_diff)

        d = {ESPID: self.cue}

        from pprint import pprint
        pprint(self.cue)

        return json.dumps(d)

def on_off():
    cue = Cue()

    for i in range(10):
        cue.append([500+i, 0], 1)
        cue.append([0, 500+i], 1)

    #print(cue.render())
    send_mqtt(TOPIC, cue.render())

if __name__ == "__main__":
    on_off()


