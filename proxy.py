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
SUCCESS = 200
NOT_FOUND = 404
SERVER_ERROR = 500

class HTTPprotocol(object):
    """
    Helper class to assist in handling the HTTP protocol.
    It has methods create http requests and responses.
    """
    delimiter = '\r\n'
    header_delimiter = 2 * delimiter
    supported_version = 1.1

    @staticmethod
    def is_supported_version(request_version: float):
        return request_version <= supported_version


class HTTPrequest(object):
    def __init__(self, method: str, uri: str, headers: dict, version = HTTPprotocol.supported_version: float):
        # process raw_request into the http request variables
        self.method = method
        self.uri = uri
        self.headers = headers
        self.version = version
        self.body = ''
    
    def __init__(self, raw_request: str):
        # process raw_request into the http request variables
        tokens = raw_request.split(HTTPprotocol.delimiter)
        method, url, raw_version = tokens[0].split(' ')
        self.__init__(method, url, {}, raw_version)
    
    def header_contains(self, key: str):
        return key in self.headers
    
    def set_body(self, body: str):
        self.body = body

    def get_method(self):
        return self.method
    
    def get_version(self):
        return self.version
    
    def get_uri(self):
        return self.uri
    
    def get_http_request(self):
        request = f'{self.method} {self.uri} HTTP/{self.version}{HTTPprotocol.delimiter}'
        for key, value in headers.items():
            request += f'{key}: {value}{HTTPprotocol.delimiter}'
        request += f'{HTTPprotocol.delimiter}{self.body}'
        return request


class HTTPresponse(object):

    status_msgs = {
        200: 'OK',
        404: 'Not Found',
        500: 'Internal Error',
    }

    def __init__(self, status_code: int):
        # put the raw response together into an http response
        self.status_code = status_code
        self.status_msg = status_msgs[status_code]
        self.version = HTTPprotocol.supported_version
        self.headers = []
        self.body = ''
    
    def set_headers(self, header_list: list):
        self.headers = header_list
    
    def set_body(self, body: str):
        self.body = body
    
    def get_http_response(self):
        response = f'HTTP/{self.version} {self.status_code} {self.status_msg}{HTTPprotocol.delimiter}'
        for header in self.headers:
            response += f"{header}{HTTPprotocol.delimiter}"
        response += f'{HTTPprotocol.delimiter}{self.body}'
        return response


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
                self.handle_connection(client)
            except Exception as e:
                print(str(e))
                self.log(f'\nServer is shutting down...\n')
                exit(0)
    
    def handle_connection(self, client: socket):
        self.log(f'Received a client connection from {client_addr}')
        # receive message
        self.log(f'Receiving message from client')
        # client_msg = self.receive(client)
        client_msg = client.recv(BUF_SZ)
        self.log(client_msg.decode('utf-8'))
        # parse message
        http_resquest = HTTPrequest(client_msg.decode('utf-8'))
        # verify if version is supported
        if not HTTPprotocol.is_supported_version(http_resquest.get_version()):
            # build response for invalid version
            http_response = HTTPresponse(SERVER_ERROR)
        else:
            # handle request based on method
            if http_resquest.get_method() == 'GET':
                self.handle_get_request(http_request)
            else:
                # build response for invalid method
                http_response = HTTPresponse(SERVER_ERROR)
        # just ECHO for now
        self.send(client, client_msg.decode('utf-8'))

        # close connection
        self.log(f'All done! Closing socket...\n\n')
        client.close()
    
    def handle_get_request(self, http_request: HTTPrequest):
        raise NotImplemented

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
