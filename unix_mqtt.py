import paho.mqtt.client as mqtt

import traceback

class MQTTClient:
    def __init__(self, clientid, remote):
        # TODO implement mqtt
        self.remote = remote
        self.client = mqtt.Client(clientid)

        self.client.on_message = self.__callback
        self.client.on_socket_open = self.__set_socket

        #def printer(*args):
        #    print(args)
        #self.client._easy_log = printer

        self.sock = None

    def __callback(self, mqtt, userdata, msg):
        try:
            if self.callback:
                self.callback(msg.topic, msg.payload)
        except Exception as e:
            print(e)
            print(traceback.format_exc())

    def __set_socket(self, client, user, socket):
        self.sock = socket.fileno()

    def set_callback(self, mqtt_callback):
        self.callback = mqtt_callback

    def connect(self):
        #self.client.on_connect = lambda a, b, c ,d: print("Connected")

        self.client.connect(self.remote)

        while self.sock is None:
            self.client.loop(timeout=1)

        #self.sock = None # assignet via on_socket_open

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def publish(self, topic, message):
        self.client.publish(topic.decode(), message)

    def check_msg(self):
        rc = self.client.loop(timeout=0)
        if rc != 0:
            # Return code 1 is broken. it is returned whenever another
            # return code would be better than "no memory"
            if rc == 1: rc = 42
            print("mqtt loop failed: ", rc, mqtt.error_string(rc))
            return False
        return True
