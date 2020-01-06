STA_IF = 1

class WLAN:
    def __init__(self, mode):
        pass

    def ifconfig(self):
        return ["192.168.0.101", "255.255.255.0", "192.168.13.37", "127.0.0.1", ]

    def isconnected(self):
        return True
