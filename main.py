import machine
try:
    import weiche
    weiche.main()
except KeyboardInterrupt:
    pass
except Exception as e:
    print("error", e)
    import sys
    sys.print_exception(e)
    machine.reset()
