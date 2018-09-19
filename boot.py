# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc
import webrepl
import time

webrepl.start()
gc.collect()

time.sleep(1)

while(True):
    try:
        import weiche
    except:
        pass
