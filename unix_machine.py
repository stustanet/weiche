"""
This is a mockup to have a 'machine' module for micropython on unix
"""
import time

class Pin:
    OUT = 1
    def __init__(self, number, direction):
        self.number = number

    def on(self):
        pass

    def off(self):
        pass


class PWM:
    def __init__(self, pin):
        self.pin = pin

    def freq(self, fhz):
        #print("Setting PWM frequency to ", fhz)
        pass

    def duty(self, duty):
        #print("Setting duty of", self.pin.number, "to", duty)
        pass

class RTC:
    def __init__(self):
        pass

    def now(self):
        return time.localtime()

    def datetime(self, new=None):
        if new is None:
            t = time.localtime()

            tim = time.time()
            subsec = int((tim - int(tim)) * 1000)
            # return 8 tupel (y, m, d, weekday, H, m, s, subs)
            return (t.tm_year, t.tm_mon, t.tm_mday, 0,
                    t.tm_hour, t.tm_min, t.tm_sec, subsec)
        else:
            # ignore time setting command
            pass



def unique_id():
    return b'\x42\x42'
