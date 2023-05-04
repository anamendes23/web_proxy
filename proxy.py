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
    """
    Static class that defines methods to store and read files from cache.
    It also has helper functions to get the formatted path and check if
    the file already exists in cache.
    This Cache class is not generic, but built to work with the Web Proxy.
    """
    root_path = './cache'
    default_file = 'root'

    def __init__(self):
        cache_dir = Path(Cache.root_path)
        if not cache_dir.exists():
            cache_dir.mkdir()

    @staticmethod
    def get_path(host: str, path: str):
        """
        Helper function that replaces the '/' characters in the path with '$'
        to create a standard file naming system for caching.

        :param host: the host in the url
        :param path: the path in the url
        :return: the formatted file path
        """
        # Note: consulted with Justin Thoreson for how to handle
        # the file path for caching
        return Path(f'{Cache.root_path}/{host}{path}')

    @staticmethod
    def contains(host: str, path: str):
        """
        Helper function to check if a file exists in cache.

        :param host: the host in the url
        :param path: the path in the url
        :return: true if the file is alredy cached
        """
        file_path = Cache.get_path(host, path)
        return file_path.exists()
    
    @staticmethod
    def cache_file(host: str, path: str, payload: str):
        """
        Function to store file in cache.

        :param host: the host in the url
        :param path: the path in the url
        :param payload: the contents of the file
        """
        dir_path = path[0:path.rindex('/')]
        dir_full_path = Cache.get_path(host, dir_path)
        dir_full_path.mkdir(parents=True, exist_ok=True)
        if dir_path == path or len(dir_path) == 0:
            path += Cache.default_file
        file_path = Cache.get_path(host, path)
        file_path.write_text(payload)
    
    @staticmethod
    def read_cache(host: str, path: str):
        """
        Function to read contents of file in cache.
        It is assumed that it has been verified that the file exists in cache.

        :param host: the host in the url
        :param path: the path in the url
        :return: the contents of the file
        """
        dir_path = path[0:path.rindex('/')]
        if dir_path == path or len(dir_path) == 0:
            path += Cache.default_file
        file_path = Cache.get_path(host, path)
        return file_path.read_text()


class HTTPprotocol(object):
    """
    Helper static class to assist in handling the HTTP protocol.
    """
    delimiter = '\r\n'
    header_delimiter = 2 * delimiter
    supported_version = 1.1

    @staticmethod
    def is_supported_version(request_version: float):
        """
        Helper function to verify if the version is supported.

        :param request_version: the version specified in the HTTP request
        :return: true if request_version is supported
        """
        return request_version <= HTTPprotocol.supported_version


class HTTPrequest(object):
    """
    Creates HTTP request following the HTTP protocol.
    It does not create a custom constructor, but two methods to populate variables
    from a raw string or with the parsed values.
    It declares accessors and modifiers for instance variables.
    """
    def __repr__(self):
        request = f'{self.method} {self.uri} HTTP/{self.version}{HTTPprotocol.delimiter}'
        for key, value in self.headers.items():
            request += f'{key}: {value}{HTTPprotocol.delimiter}'
        request += f'{HTTPprotocol.delimiter}{self.body}'
        return request
    
    def populate(self, method: str, uri: str, version = HTTPprotocol.supported_version):
        """
        Update values of HTTPrequest. Heades and body and left empty.

        :param method: HTTP method
        :param uri: HTTP uri
        :param version: HTTP version
        """
        # process raw_request into the http request variables
        self.method = method
        self.uri = uri
        self.headers = {}
        self.version = float(version)
        self.body = ''
    
    def build_from_raw(self, raw_request: str):
        """
        Parses a raw string to populate HTTP request values.

        :param raw_request: a string containing the HTTP request
        """
        # process raw_request into the http request variables
        tokens = raw_request.split(HTTPprotocol.delimiter)
        method, url, raw_version = tokens[0].split(' ')
        version = raw_version.split('HTTP/')[1]
        self.populate(method, url, version)
    
    def add_headers(self, *kvp):
        """
        Adds a list of key-value pairs to the HTTP request headers.
        Expected as input: key (str), followed by respective value

        :param *kvp: key-value pairs
        """
        for i in range(0, len(kvp), 2):
            self.headers[kvp[i]] = kvp[i+1]

    def append_headers(self, headers_dict: dict):
        """
        Appends a headers dictionary to the instance headers.

        :param headers_dict: to be added to existing dictionary
        """
        self.headers.update(headers_dict)

    def set_body(self, body: str):
        """ Modifier for HTTP request body """
        self.body = body

    def get_method(self):
        """ Accessor for HTTP method """
        return self.method
    
    def get_version(self):
        """ Accessor for HTTP version """
        return self.version
    
    def get_uri(self):
        """ Accessor for HTTP uri """
        return self.uri
    
    def get_headers(self):
        """ Accessor for HTTP headers """
        return self.headers


class HTTPresponse(object):
    """
    Creates HTTP response following the HTTP protocol.
    It declares accessors and modifiers for instance variables.
    """
    status_msgs = {
        200: 'OK',
        404: 'Not Found',
        500: 'Internal Error',
    }

    def __init__(self, status_code: int, default_headers: bool = True):
        # put the raw response together into an http response
        self.status_code = status_code
        self.status_msg = HTTPresponse.status_msgs[status_code]
        self.version = HTTPprotocol.supported_version
        self.headers = self.get_default_headers() if default_headers else {}
        self.body = ''
    
    def __repr__(self):
        response = f'HTTP/{self.version} {self.status_code} {self.status_msg}{HTTPprotocol.delimiter}'
        for key, value in self.headers.items():
            response += f"{key}: {value}{HTTPprotocol.delimiter}"
        response += f'{HTTPprotocol.delimiter}{self.body}'
        return response
    
    def get_default_headers(self):
        return {
            'Connection': 'close',
            'Cache-Hit': '0'
        }
    
    def add_headers(self, *kvp):
        """
        Adds a list of key-value pairs to the HTTP response headers.
        Expected as input: key (str), followed by respective value

        :param *kvp: key-value pairs
        """
        for i in range(0, len(kvp), 2):
            self.headers[kvp[i]] = kvp[i+1]

    def append_headers(self, headers_dict: dict):
        """
        Appends a headers dictionary to the instance headers.

        :param headers_dict: to be added to existing dictionary
        """
        self.headers.update(headers_dict)
    
    def set_body(self, body: str):
        """ Modifier for HTTP response body """ 
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
        """
        Creates a socket that listenst at (HOST, port)

        :param port: the port number that the socket will listen at
        :return: the socket and its address
        """
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
        """ Proxy loop that listens to incoming connections """
        while True:
            try:
                self.log(f' ******************** Ready to serve ********************')
                client, client_addr = self.listener.accept()
                self.log(f'Received a client connection from {client_addr}')
                self.handle_connection(client)
            except KeyboardInterrupt as e:
                self.listener.close()
                self.log(f'\nServer is shutting down...\n')
                exit(0)
    
    def handle_connection(self, client: socket):
        """ 
        Communicates with client to fulfill the incoming requests using the HTTP protocol.
        It only supports GET operations and it checks the cache before contacting the web server.

        :param client: socket from client connection
        """
        try:
            headers, payload = self.receive(client)
            self.log(f'Received a message from this client: {headers}{payload}')
        except:
            self.log(f'Malformed message from client...')
            http_response = HTTPresponse(SERVER_ERROR)
        else:
            http_response = self.handle_http_request(headers, payload)

        self.log(f'Now responding to the client...')
        self.send(client, str(http_response))

        self.log(f'All done! Closing socket...\n\n')
        client.close()
    
    def handle_http_request(self, headers: str, payload: str):
        """
        Gets the data received by the client, parses it into an HTTPrequest object
        and handles the request.

        :param headers: the raw headers of the request
        :param payload: the payload of the request
        :return: the http response to be sent back to the client
        """
        try:
            http_request = HTTPrequest()
            http_request.build_from_raw(headers)
            http_request.set_body(payload)
        except:
            return HTTPresponse(SERVER_ERROR)

        if not HTTPprotocol.is_supported_version(http_request.get_version()):
            self.log(f'Oops, this HTTP version ({http_request.get_version()}) is not supported!')
            http_response = HTTPresponse(SERVER_ERROR)
        else:
            if http_request.get_method() == 'GET':
                http_response = self.handle_get_request(http_request)
            else:
                self.log(f'HTTP method {http_request.get_method()} not supported...')
                http_response = HTTPresponse(SERVER_ERROR)
        
        return http_response

    def handle_get_request(self, http_request: HTTPrequest):
        """
        Fulfill client's HTTP GET request
        
        :param http_request: the client's HTTP request
        :return: an HTTP response
        """
        parsed_url = urlparse(http_request.get_uri())
        host = parsed_url.hostname
        path = parsed_url.path if len(parsed_url.path) > 0 else '/'
        if Cache.contains(host, path):
            return self.handle_cache_hit(host, path)
        else:
            return self.handle_cache_miss(host, path, http_request)

    def handle_cache_hit(self, host: str, path: str):
        """
        Handle a GET request with cache hit.

        :param host: the host in the url
        :param path: the path in the url
        :return: an HTTP response
        """
        self.log(f'Yay! The requested file is in the cache...')
        http_response = HTTPresponse(SUCCESS, False)
        payload = Cache.read_cache(host, path)
        http_response.set_body(payload)
        http_response.add_headers('Content-length', len(payload), 'Connection', 'close', 'Cache-Hit', 1)
        return http_response
    
    def handle_cache_miss(self, host, path, http_request):
        """
        Handle a GET request with cache miss.

        :param host: the host in the url
        :param path: the path in the url
        :http_request: the client's HTTP request
        :return: an HTTP response
        """
        self.log(f'Oops! No cache hit! Requesting origin server for the file...')
        server_request = HTTPrequest()
        server_request.populate(http_request.method, path)
        server_request.add_headers('Host', host, 'Connection', 'close')
        server_request.append_headers(http_request.get_headers())
        try:
            headers, payload = self.contact_server(host, server_request)
            tokens = headers.split(HTTPprotocol.delimiter)
            first_line_tokens = tokens[0].split(' ')
            status_code = int(first_line_tokens[1])
        except:
            self.log(f'There was an issue contacting the server...')
            return HTTPresponse(SERVER_ERROR)
        
        http_response = ''.join([headers, '\r\nCache-Hit: 0', HTTPprotocol.header_delimiter, payload])
        if status_code == SUCCESS:
            self.log(f'Response received from server, and status code is 200! Write to cache, save time next time...')
            Cache.cache_file(host, path, payload)
            return http_response

        self.log(f'Response received from server, but status code is not 200! No cache writing...')
        if status_code in HTTPresponse.status_msgs:
            return http_response
        else:
            http_response = HTTPresponse(SERVER_ERROR)
            http_response.set_body(payload)
            return http_response

    def contact_server(self, host: str, http_request: HTTPrequest):
        """
        Uses a socket to make an HTTP request to the web server.

        :param host: the web server host
        :param http_request: the HTTP request to send to the server
        :return: the data received from the server
        """
        self.log(f'Sending the following message from proxy to server:')
        self.log(str(http_request))
        with socket(AF_INET, SOCK_STREAM) as proxy_sock:
            proxy_sock.connect((host, PORT))
            self.send(proxy_sock, str(http_request))
            return self.receive(proxy_sock)
    
    def receive(self, sock: socket):
        """
        Helper function to receive incoming data using sockets.
        This function expects the message to follow the HTTP protocol.

        :param sock: the socket used in the connection
        :return: headers and payload of message
        """
        headers = b''
        payload = b''
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
        """
        Helper function to send data via socket.

        :param sock: the socket used in the connection
        :param data: the decoded data to be sent
        """
        sock.sendall(bytes(data, 'utf-8'))
    
    def log(self, message):
        """
        Helper function to print statements in desired format.

        :param message: to be print to console
        """
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
