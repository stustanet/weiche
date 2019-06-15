import machine
import time

time.sleep(1)


while(True):
    try:
        import weiche
    except KeyboardInterrupt:
        # If we got a keyboard interrupt, we leave the loop.
        break
    except Exception as e:
        # Any other exception: Just restart the CPU
        print(e)
        machine.reset()

