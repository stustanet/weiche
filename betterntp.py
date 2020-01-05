import time

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
    RTC = RTC()

    def nowfloat(self):
        # returns 8 tupel (y, m, d, weekday, H, m, s, subs)
        nowstamp = self.RTC.datetime()

        mktimetupel = (nowstamp[0], nowstamp[1], nowstamp[2],
                       nowstamp[4], nowstamp[5], nowstamp[6],
                       0, 0, -1)

        # wants 9 tupel (y, m, d, h, m, s, weekday, yearday)
        timenow = time.mktime(mktimetupel)

        #print("timenow", timenow)
        #print("nowstamp", nowstamp)
        timenow += nowstamp[7] / DATETIMEFACTOR # 10e3  # milliseconds
        #print("timefloat", timenow)
        return timenow


    def ntptime(self):
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1b
        addr = socket.getaddrinfo(self.host, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.settimeout(0.5)
            start = self.nowfloat()
            res = s.sendto(NTP_QUERY, addr)
            msg = s.recv(48)
            end = self.nowfloat()
        except OSError as ex:
            print("Failed to update time: ", ex)
            return None, None
        finally:
            s.close()
        (s, ms) = struct.unpack("!II", msg[40:48])

        if s == 0:
            print("BADNTP")

        rtt = (end-start)/2
        ms = ms * NTP_FRACTION + rtt
        if ms > 1:
            s += 1
            ms -= 1

        return (s - NTP_DELTA, int(ms * 1000))

    # There's currently no timezone support in MicroPython, so
    # utime.localtime() will return UTC time (as if it was .gmtime())
    def update(self):
        (s, ms) = self.ntptime()
        if s is None or ms is None:
            return

        tm = time.localtime(s)
        tup = (tm[0], tm[1], tm[2], 0, tm[3] + 1, tm[4], tm[5], ms)
        #print("tm", tm, "arg", tup, "len", len(tup))
        self.RTC.datetime(tup)

        print("[*] Updated time to %02i-%02i-%02iT%02i:%02i:%02i.%04i"%(
            tm[0], tm[1], tm[2], tm[3]+1, tm[4], tm[5], ms))

    def set_host(self, hostname):
        self.host = hostname

if __name__=="__main__":
    s, ms = time()
    print(s, ms)
    import time
    tm = time.localtime(s)
    print(tm)
