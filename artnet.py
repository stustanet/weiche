#!/usr/bin/env python3

"""
A micropython / python compatible artnet receiver packet
"""

#pylint: disable=broad-except

import struct

try:
    import socket
    import time

except ImportError:
    # Micropython compatibility measurements
    import usocket as socket
    import utime as time

ARTNET_MAGIC = b"Art-Net\0"

class ArtNetPacket:
    """
    Representation of an Art-Net packet
    """
    #pylint: disable=invalid-name
    Magic = ARTNET_MAGIC
    Opcode = 0x50
    Version = 14
    Sequence = 42
    Physical = 0
    Universe = 0
    Length = 0
    Data = bytes()

    _fmt = "!hhbbhh"
    def unpack(self, data):
        """
        unpack it from the given bytes() buffer
        """
        #self.Magic = data[0:8]

        self.Opcode, \
            self.Version, \
            self.Sequence, \
            self.Physical, \
            self.Universe, \
            self.Length \
            = struct.unpack(self._fmt, data[8:18])
        self.Data = data[18:]

    def pack(self, update=True):
        """
        pack it into a bytes() buffer and return the created buffer
        """
        if update:
            if len(self.Data) % 2 != 0:
                self.Data += [0]
            self.Length = len(self.Data)

        data = bytes()
        data += ARTNET_MAGIC
        data += struct.pack(self._fmt,
                            self.Opcode,
                            self.Version,
                            self.Sequence,
                            self.Physical,
                            self.Universe,
                            self.Length)
        data += self.Data
        return data


class ArtNetController:
    """
    Listen to artnet messages and call a callback whenever one was received
    """

    NUMBER_OF_CHANNELS = 8

    def __init__(self, light_callback):
        # \param light_callback: coroutine to be called for a new artnet config
        self.config = None
        self.light_callback = light_callback
        self.socket = None
        self.remote = None

    def setconfig(self, config):
        """ update the stored config """
        self.config = config

    def init_broadcast_receiver(self):
        """
        initialize the socket to receive broadcasts
        """
        if self.socket:
            self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(False)
        self.socket.bind(("", 6454))

    def run(self):
        """
        Run forever and call the light_callback given in __init__ whenever a
        new message was received.
        """

        self.init_broadcast_receiver()
        self.socket.setblocking(True)
        while True:
            try:
                while True:
                    if not self.run_once():
                        break

            except Exception as exc:
                print("mainloop", exc)
                # For the moment, later we will catchall
            except KeyboardInterrupt:
                break
            time.sleep(1)

    def run_once(self):
        """
        this is to be used if it is included in a select() structure
        """

        try:
            data, self.remote = self.socket.recvfrom(1024)
        except OSError as err:
            #if e.errno == errno.EWOULDBLOCK:
            #    # Some hickup in the select business happened. Ignore.
            #    return True
            #else:
            print("err", err)
            return False

        if data is None:
            return False

        if data == b"":
            raise OSError("disconnected")

        if not self.config:
            # tried to wait for a broadcast packet, and now
            # retry receiving a config!
            return False

        self.handle_message(data)
        return True


    def handle_message(self, data):
        """
        Check the message for inconsistencies and call the light callback if
        everything matched up

        Returning True means the connection is still ok
        """

        packet = ArtNetPacket()
        try:
            packet.unpack(data)
        except struct.error:
            print("could not decode packet: struct error")
            return

        if packet.Magic != b"Art-Net\0":
            print("Invalid artnet packet: magic")
            return

        if packet.Opcode != 0x50:
            print("No DMX packet")
            return

        if packet.Version != 14:
            print("Invalid protocol version")
            return

        if packet.Universe != int(self.config.config('artnet', 'universe')):
            print("not my universe")
            return

        # grab the right subset of the buffer
        my_dmx = self.config.config('artnet', 'start_address')
        data = packet.Data[my_dmx:my_dmx + self.NUMBER_OF_CHANNELS]

        self.light_callback(list(data))

def test_callback(msg):
    """
    Used only for testing
    """
    print("received control", msg)

def main():
    """
    Used only for testing and documentation reasons
    """
    ctrl = ArtNetController(test_callback)
    ctrl.run()

if __name__ == "__main__":
    main()
