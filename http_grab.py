"""
Just a quick and dirty far from feature complete http requestor
- that does support timeouts!
"""

try:
    import usocket as socket
    #import uselect as select
except ImportError:
    import socket
    #import select

def get(host, port, url, timeout=1):
    """
    This is the worst http request library you know - but it does
    timeouts, which makes it more usable than any other http library for
    micropython on the market as of 01/2020.
    """
    sock = socket.socket()

    sock.settimeout(timeout)
    sockaddr = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0][-1]
    sock.connect(sockaddr)

    sock.send(("GET %s HTTP/1.1\r\n"%url
               + "Host: %s\r\n"%host
               + "\r\n").encode('ascii'))

    data = bytearray()
    while True:
        recv = sock.recv(512)
        if not recv:
            break
        data += recv

    expected_prefix = b'HTTP/1.0 200 OK'
    if data[0:len(expected_prefix)] != expected_prefix:
        return None

    msg = data.decode('utf-8')
    del data

    idx = msg.find("\r\n\r\n")
    if idx == -1:
        return None

    msg = msg[idx+4:]

    return msg
