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
PORT = 80
BUF_SZ = 4096
TIMEOUT = 5 # seconds
SUCCESS = 200
NOT_FOUND = 404
SERVER_ERROR = 500

class Cache(object):
    root_path = './cache'

    def __init__(self):
        cache_dir = Path(Cache.root_path)
        if not cache_dir.exists():
            cache_dir.mkdir()

    @staticmethod
    def get_path(host: str, path: str):
        raw_path = f'{host}{path}'.replace('/', '$')
        return Path(f'{Cache.root_path}/{raw_path}')

    @staticmethod
    def contains(host: str, path: str):
        file_path = Cache.get_path(host, path)
        return file_path.exists()
    
    @staticmethod
    def cache_file(host: str, path: str, payload: str):
        file_path = Cache.get_path(host, path)
        file_path.write_text(payload)
    
    @staticmethod
    def read_cache(host: str, path: str):
        file_path = Cache.get_path(host, path)
        return file_path.read_text()


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
        return request_version <= HTTPprotocol.supported_version


class HTTPrequest(object):
    def __repr__(self):
        request = f'{self.method} {self.uri} HTTP/{self.version}{HTTPprotocol.delimiter}'
        for key, value in self.headers.items():
            request += f'{key}: {value}{HTTPprotocol.delimiter}'
        request += f'{HTTPprotocol.delimiter}{self.body}'
        return request
    
    def instantiate(self, method: str, uri: str, version = HTTPprotocol.supported_version):
        # process raw_request into the http request variables
        self.method = method
        self.uri = uri
        self.headers = {}
        self.version = float(version)
        self.body = ''
    
    def build_from_raw(self, raw_request: str):
        # process raw_request into the http request variables
        tokens = raw_request.split(HTTPprotocol.delimiter)
        method, url, raw_version = tokens[0].split(' ')
        version = raw_version.split('HTTP/')[1]
        self.instantiate(method, url, version)

    def header_contains(self, key: str):
        return key in self.headers
    
    def add_headers(self, *kvp):
        for i in range(0, len(kvp), 2):
            self.headers[kvp[i]] = kvp[i+1]

    def append_headers(self, headers_dict: dict):
        self.headers.update(headers_dict)

    def set_body(self, body: str):
        self.body = body

    def get_method(self):
        return self.method
    
    def get_version(self):
        return self.version
    
    def get_uri(self):
        return self.uri
    
    def get_headers(self):
        return self.headers


class HTTPresponse(object):

    status_msgs = {
        200: 'OK',
        404: 'Not Found',
        500: 'Internal Error',
    }

    def __init__(self, status_code: int):
        # put the raw response together into an http response
        self.status_code = status_code
        self.status_msg = HTTPresponse.status_msgs[status_code]
        self.version = HTTPprotocol.supported_version
        self.headers = {}
        self.body = ''
    
    def __repr__(self):
        response = f'HTTP/{self.version} {self.status_code} {self.status_msg}{HTTPprotocol.delimiter}'
        for header in self.headers:
            response += f"{header}{HTTPprotocol.delimiter}"
        response += f'{HTTPprotocol.delimiter}{self.body}'
        return response
    
    def add_headers(self, *kvp):
        for i in range(0, len(kvp), 2):
            self.headers[kvp[i]] = kvp[i+1]

    def append_headers(self, headers_dict: dict):
        self.headers.update(headers_dict)
    
    def set_body(self, body: str):
        self.body = body


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
            except KeyboardInterrupt as e:
                self.log(f'\nServer is shutting down...\n')
                exit(0)
            except Exception as e:
                print(str(e))
                exit(1)
    
    def handle_connection(self, client: socket):
        headers, payload = self.receive(client)
        self.log(f'Received a message from this client: {headers}{payload}')

        http_request = HTTPrequest()
        http_request.build_from_raw(headers)
        http_request.set_body(payload)

        if not HTTPprotocol.is_supported_version(http_request.get_version()):
            http_response = HTTPresponse(SERVER_ERROR)
        else:
            if http_request.get_method() == 'GET':
                http_response = self.handle_get_request(http_request)
            else:
                http_response = HTTPresponse(SERVER_ERROR)

        self.log(f'Now responding to the client...')
        self.send(client, str(http_response))

        self.log(f'All done! Closing socket...\n\n')
        client.close()
    
    def handle_get_request(self, http_request: HTTPrequest):
        parsed_url = urlparse(http_request.get_uri())
        host = parsed_url.hostname
        path = parsed_url.path if len(parsed_url.path) > 0 else '/'
        if Cache.contains(host, path):
            return self.handle_cache_hit(host, path)
        else:
            return self.handle_cache_miss(host, path, http_request)

    def handle_cache_hit(self, host: str, path: str):
        self.log(f'Yay! The requested file is in the cache...')
        http_response = HTTPresponse(SUCCESS)
        payload = Cache.read_cache(host, path)
        http_response.set_body(payload)
        http_response.add_headers('Content-length', len(payload), 'Connection', 'close')
        return http_response
    
    def handle_cache_miss(self, host, path, http_request):
        self.log(f'Oops! No cache hit! Requesting origin server for the file...')
        server_request = HTTPrequest()
        server_request.instantiate(http_request.method, path)
        server_request.add_headers('Host', host, 'Connection', 'close')
        server_request.append_headers(http_request.get_headers())
        headers, payload = self.contact_server(host, server_request)
        tokens = headers.split(HTTPprotocol.delimiter)
        first_line_tokens = tokens[0].split(' ')
        status_code = int(first_line_tokens[1])
        if status_code == SUCCESS:
            self.log(f'Response received from server, and status code is 200! Write to cache, save time next time...')
            Cache.cache_file(host, path, payload)
            return self.handle_cache_hit(host, path)

        self.log(f'Response received from server, but status code is not 200! No cache writing...')
        if status_code in HTTPresponse.status_msgs:
            return HTTPresponse(status_code)
        else:
            return HTTPresponse(SERVER_ERROR)

    def contact_server(self, host: str, http_request: HTTPrequest):
        self.log(f'Sending the following message from proxy to server:')
        self.log(str(http_request))
        with socket(AF_INET, SOCK_STREAM) as proxy_sock:
            proxy_sock.connect((host, PORT))
            self.send(proxy_sock, str(http_request))
            return self.receive(proxy_sock)
    
    def receive(self, sock: socket):
        headers = b''
        payload = b''
        endl = bytes(HTTPprotocol.delimiter, 'utf-8')
        header_endl = bytes(HTTPprotocol.header_delimiter, 'utf-8')

        while True:
            temp = sock.recv(BUF_SZ)
            headers = b''.join([headers, temp])
            if len(temp) < BUF_SZ or temp.find(header_endl) > -1:
                break
        
        tokens = headers.decode('utf-8').split(HTTPprotocol.header_delimiter)
        headers = tokens[0]
        if len(tokens) > 1:
            payload = b''.join([payload, bytes(tokens[1], 'utf-8')])
        size = 0
        received = len(payload)
        for line in headers.split(HTTPprotocol.delimiter):
            if line.lower().find('content-length:') > -1:
                size = int(line.split(':')[1].strip())
                break

        while received < size:
            temp = sock.recv(BUF_SZ)
            if not temp:
                break
            received += len(temp)
            payload = b''.join([payload, temp])

        return headers, payload.decode('utf-8')
    
    def send(self, sock, data):
        sock.sendall(bytes(data, 'utf-8'))
    
    def log(self, message):
        print(message)


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 proxy.py port')
        exit(1)
    
    port = int(sys.argv[1])
    cache = Cache()
    server = ProxyServer(port)


if __name__ == '__main__':
    main()
