# Web Proxy

The web proxy sits between the web client and the web server to relay HTTP traffic.

Generally, when the client makes a request, the request is sent to the web server. The web server then processes the request and sends back a response message to the requesting client. In order to improve the performance, we create a proxy server between the client and the web server. Now, both the request message sent by the client and the response message delivered by the web server pass through the proxy server.

## Web Proxy Support

### HTTP Version
* 1.1

### HTTP Methods
* GET

## Usage

$ python3 proxy.py port
