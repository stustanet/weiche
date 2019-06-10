import machine

time.sleep(1)


while(True):
    try:
        import weiche
    except KeyboardInterrupt:
        # If we got a keyboard interrupt, we leave the loop.
        break
    except:
        # Any other exception: Just restart the CPU
        machine.reset()

