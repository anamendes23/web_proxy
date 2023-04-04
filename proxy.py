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
$ python3 proxy.py port

"""

from socket import *
import sys
from urllib.parse import urlparse
from pathlib import Path

BACKLOG = 5 # listener queue size
HOST = 'localhost'
BUF_SZ = 4096
SERVER_ADDR = ('css1.seattleu.edu', 80)
TIMEOUT = 5 # seconds

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
        self.listener, self.listener_address = self.create_socket(port)
        self.log(f'Listening at {self.listener_address}')
        self.start_proxy()
    
    def create_socket(self, port: int):
        try:
            listener = socket(AF_INET, SOCK_STREAM)
            address = (HOST, port)
            listener.bind(address)
            listener.listen(BACKLOG)
            return listener, address
        except Exception as e:
            self.log(f'Unable to connect to address ({HOST}, {port})\n{str(e)}')
            exit(1)
    
    def start_proxy(self):
        while True:
            try:
                self.log(f' ******************** Ready to serve ********************')
                client, client_addr = self.listener.accept()
                self.log(f'Received a client connection from {client_addr}')
                self.handle_connection(client)
                self.log(f'All done! Closing socket...\n\n')
                client.close()
            except Exception as e:
                print(str(e))
                self.log(f'\nServer is shutting down...\n')
                exit(0)
    
    def handle_connection(self, client: socket):
        # receive message

        # parse message

        # verify if version is supported

        # verify if method is supported

        # handle request based on method

        self.log(f'Receiving message from client')
        client_msg = self.receive(client)
        self.log(client_msg.decode('utf-8'))
        self.send(client, client_msg.decode('utf-8'))

    def contact_server(self, client_request):
        with socket(AF_INET, SOCK_STREAM) as proxy_sock:
            proxy_sock.connect(SERVER_ADDR)
            self.send(proxy_sock, client_request)
            return self.receive(proxy_sock)
    
    def receive(self, sock):
        sock.settimeout(TIMEOUT)
        data = bytearray()
        while True:
            try:
                temp = sock.recv(BUF_SZ)
                # print(temp)
                if len(temp) <= 0:
                    break
                data.extend(temp)
            except Exception as e:
                print(str(e))
                break
        self.log(f'Received a message from this client: {data}')
        return data
    
    def send(self, sock, data):
        sock.sendall(bytes(data, 'utf-8'))
    
    def log(self, message):
        print(message)


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 proxy.py port')
        exit(1)
    
    port = int(sys.argv[1])
    server = ProxyServer(port)


if __name__ == '__main__':
    main()
