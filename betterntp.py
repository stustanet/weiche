"""
Implement a basic NTP interface that is able to set the local time
io the controller as well as give the current time including millisecond
accuracy as float
"""

try:
    import usocket as socket
    import ustruct as struct
    import utime as time
except ImportError:
    import socket
    import struct
    import time

try:
    from machine import RTC
    # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
    # Micropython uses the EPOCH 1.1.2000. Those retards.
    NTP_DELTA = 3155673600
    DATETIMEFACTOR = 1000000
except ImportError:
    from unix_machine import RTC
    # (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
    NTP_DELTA = 2208988800
    DATETIMEFACTOR = 1000

NTP_FRACTION = 1 / (2**32)

class BetterNTP:
    """
    Timing interface for not so fancy ntp interfacing
    """
    RTC = RTC()
    host = "pool.ntp.org"

    def nowfloat(self):
        """
        return the current time since 2000-01-01T00:00:00.0000
        in seconds including fractions of a second - just
        as we know time.time() on normal python
        """

        # returns 8 tupel (y, m, d, weekday, H, m, s, subs)
        nowstamp = self.RTC.datetime()

        mktimetupel = (nowstamp[0], nowstamp[1], nowstamp[2],
                       nowstamp[4], nowstamp[5], nowstamp[6],
                       0, 0, -1)

        # wants 9 tupel (y, m, d, h, m, s, weekday, yearday)
        timenow = time.mktime(mktimetupel)

        timenow += nowstamp[7] / DATETIMEFACTOR # 10e3  # milliseconds
        return timenow


    def ntptime(self):
        """
        Perform a query to the configured NTP server and return the time measured.
        """
        addr = socket.getaddrinfo(self.host, 123)[0][-1]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            sock.settimeout(0.5)
            query = bytearray(48)
            query[0] = 0x1b
            start = self.nowfloat()
            sock.sendto(query, addr)
            msg = sock.recv(48)
            end = self.nowfloat()
        except OSError as ex:
            print("Failed to update time: ", ex)
            return None, None
        finally:
            sock.close()
        (sec, msec) = struct.unpack("!II", msg[40:48])

        if sec == 0:
            # if the seconds returned are 0, then we will not
            # accept such a packet
            print("BADNTP")
            return None, None

        rtt = (end-start)/2
        msec = msec * NTP_FRACTION + rtt
        if msec > 1:
            sec += 1
            msec -= 1

        return (sec - NTP_DELTA, int(msec * 1000))

    # There's currently no timezone support in MicroPython, so
    # utime.localtime() will return UTC time (as if it was .gmtime())
    def update(self):
        """
        request the time from ntp and update the controllers time
        """
        (sec, msec) = self.ntptime()
        if sec is None or msec is None:
            return

        loct = time.localtime(sec)
        tup = (loct[0], loct[1], loct[2], 0, loct[3] + 1, loct[4], loct[5], msec)
        #print("loct", loct, "arg", tup, "len", len(tup))
        self.RTC.datetime(tup)

        print("[*] Updated time to %02i-%02i-%02iT%02i:%02i:%02i.%04i"%(
            loct[0], loct[1], loct[2], loct[3]+1, loct[4], loct[5], msec))

    def set_host(self, hostname):
        """
        set the host to contact for ntp
        """
        self.host = hostname

def test():
    """ Basic testing """
    ntp = BetterNTP()
    sec, msec = ntp.ntptime()
    print(sec, msec)
    print(time.localtime(sec))


if __name__ == "__main__":
    test()
