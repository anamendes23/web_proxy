"""
CPSC 5510, Seattle University
This is free and unencumbered software released into the public domain.
:Authors: Ana Mendes
:Version: 1.0

Web Proxy
The web proxy sits between the web client and the web server to relay HTTP traffic.
Generally, when the client makes a request, the request is sent to the web server.
The web server then processes the request and sends back a response message to the
requesting client. In order to improve the performance, we create a proxy server
between the client and the web server. Now, both the request message sent by the
client and the response message delivered by the web server pass through the proxy
server.

Usage:
$python3 proxy.py port

"""

from socket import *
import sys
from urllib.parse import urlparse
from pathlib import Path

class ProxyServer(object):
    """
    The Proxy Server object will receive client requests, check its cache.
    If the cache contain the information request, it responds to the client.
    If not, it forwards the request to the web server, caches the response and
    sends the response to the client.
    
    Supported HTTP version: 1.1
    Supported methods: GET
    """

    def __init__(self, port: int):
        self.port = port
        print("Proxy server")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 proxy.py port")
        exit(1)
    
    server = ProxyServer(sys.argv[1])


if __name__ == '__main__':
    main()
