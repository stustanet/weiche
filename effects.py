import utime

class EffectQueue:
    """
    Store effects in a queue.
    An effect consists of a global time to activate and the values to set.

    time to activate is in integer milliseconds since 2000.01.01T00:00:00.0000

    This is done to avoid floating point errors.
    uPy is capable of infinite large integers, they just get quite inefficient.
    """

    def __init__(self, config, ntp, set_lights):
        # list of [[time, [0, 0, 0, 0, 0, 0, 0, 0]], ...] values
        self.queue = []

        self.config = config
        self.ntp = ntp
        self.set_lights = set_lights


    def update(self, new):
        """
        New elements are defined as a list
        [[start, [led_vals * 8]], ...].

        Start is the float value of seconds since 1.1.2000. *yay*
        Upon updating all elements that are after the first inserted element
        will be removed.
        If this method is called with an empty list, the queue is cleared.
        """
        if not new:
            # Empty list, clear the full list.
            self.queue = []
            return

        print("Age of first element in new cue: ", self.age(new[0][0]))
        while self.queue and self.queue[0][0] > new[0][0]:
            self.queue.pop(0)

        self.queue = self.queue + new

        while self.queue and self.age(self.queue[0][0]) > 0:
            self.queue.pop(0)


    def active(self):
        return len(self.queue) > 0

    def age(self, elementtime):
        """
        Element time is in milliseconds
        """

        # local time in seconds and milliseconds
        # returns 8 tupel (y, m, d, WEEKDAY, H, m, s, subs)
        # used for subseconds
        dt = self.ntp.RTC.datetime()
        ltsec = utime.mktime((dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[2], 0, 0))
        ltmsec = dt[7] // 1000

        #ltmsec = self.ntp.RTC.datetime()[7] / 1000
        #ltsec = utime.time()

        # returns 9 tupel (y, m, d, h, m, s WEEKDAY, yearday
        #lt = utime.localtime()
        #et = utime.localtime(int(elementtime/1000))

        # element time in seconds and milliseconds
        etmsec = elementtime%1000
        etsec = elementtime // 1000

        dsec = ltsec - etsec
        dmsec = ltmsec - etmsec

        diff = dsec + dmsec / 1000

        if diff >= 0:
            print("local %6d"%ltsec, "local msec %3d"%ltmsec,
                  "element %6d"%etsec, "el msec %3d"%etmsec,
                  "dsec %4.2f"%dsec,
                  "dmsec %4d"%dmsec,
                  "diff %4.4f"%diff)

        return diff


    def trigger(self):
        """
        Check if the local time is > than the first element in the queue,
        and activate it.
        """
        if self.queue and self.age(self.queue[0][0]) >= 0:
            # enable next effect
            self.set_lights(self.queue[0][1])
            # normally remove the first element
            self.queue.pop(0)

        while self.queue and self.age(self.queue[0][0]) > 0:
            print("Skipping front of queue", self.queue[0], "because age is ", self.age(self.queue[0][0]))
            self.queue.pop(0)
            self.queue = []

        if not self.queue:
            self.set_lights(self.config.config('idle', 'lights'))


    def debug(self):
        for s in self.queue:
            time_to_go = self.age(s[0])

            print("%5.2f  %s"%(time_to_go, str(s)))
