import sys
import socket
from socket import *
import requests
import ssl

def parseUrl(url):
    if url[4] == ':':
        port = 80
        if url.find('/', 7) != -1:
            host = url[7:url.find('/', 7)]
            path = url[url.find('/', 7):len(url) - 1]
        else:
            host = url[7:len(url) - 1]
            path = '/'
    else:
        port = 443
        if url.find('/', 8) != -1:
            host = url[7:url.find('/', 8)]
            path = url[url.find('/', 8):len(url) - 1]
        else:
            host = url[8:len(url) - 1]
            path = '/'
    return port, host, path

def networkError():
    print('Status: Network Error\n')

class HttpClientSocket:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clientSocket = socket(AF_INET, SOCK_STREAM)

    def connectTCP(self):
        self.clientSocket = socket(AF_INET, SOCK_STREAM)
        try:
            self.clientSocket.connect((self.host, self.port))
            if self.port == 443:
                self.clientSocket = ssl.wrap_socket(self.clientSocket, ssl_version=ssl.PROTOCOL_TLS)
        except Exception as e:
            networkError()
            self.clientSocket.close()
            return False
        return True 

    def requestMessage(self, path):
        if self.connectTCP():
            request = f'GET {path} HTTP/1.0\r\n'
            request += f'Host: {self.host}\r\n'
            request += f'Connection: close\r\n'
            request += '\r\n'
            try:
                self.clientSocket.send(request.encode())
            except Exception as e:
                networkError()
                self.clientSocket.close()
                return False
            return True

    def getRespondMessage(self):
        response = ""
        try:
            while True:
                data = self.clientSocket.recv(4096)
                if not data:
                    break;
                response += data.decode()
                status = response
                if status.find('404 Not Found') != -1:
                    print('Status: 404 Not Found\n')
                    break
                elif status.find('301 Moved Permanently') != -1:
                    print('Status: 301 Moved Permanently\n')
                    self.redirectUrl(status)
                    break
                elif status.find('302 Found') != -1:
                    print('Status: 302 Found\n')
                    self.redirectUrl(status)
                    break
                elif status.find('200 OK') != -1:
                    print('Status: 200 OK\n')
                    self.fetchRefObj(status)
                    break
                elif status.find('400 Bad Request') != -1:
                    print('Status: 400 Bad Request\n')
                    break
                elif status.find('505 HTTP Version Not Supported') != -1:
                    print('Status: 505 HTTP Version Not Supported\n')
                    break
                elif status.find('403 Forbidden') != -1:
                    print('Status: 403 Forbidden\n');
                    break
        except Exception as e:
            networkError()
            self.clientSocket.close()

    def redirectUrl(self, respondMessage):
        lines = respondMessage.split("\r\n")
        for line in lines:
            if line.startswith("Location: "):
                newUrl = line[len("Location: "):len(line)] + ' '
                print('Redirected URL: ' + newUrl + '\n')
                newPort, newHost, newPath = parseUrl(newUrl)
                self.host = newHost
                self.port = newPort
                if self.requestMessage(newPath):
                    self.getRespondMessage()

    def fetchRefObj(self, respondMessage):
        lines = respondMessage.split("\n")
        referencedUrls = []
        for line in lines:
            if line.find('<img', 0) != -1:
                src = line[line.find('=') + 2:line.find(' ', line.find('=')) - 1]
                if src.startswith("http://") or src.startswith("https://"):
                    referencedUrl = src + ' '
                    newPort, newHost, newPath = parseUrl(referencedUrl)
                    self.host = newHost
                    self.port = newPort
                else:
                    newPath = src
                    if self.port == 80:
                        referencedUrl = 'http://' + self.host + src
                    else:
                        referencedUrl = 'https://' + self.host + src
                print('Referenced URL: ' + referencedUrl + '\n')
                if self.requestMessage(newPath):
                    resImage = requests.get(referencedUrl)
                    if resImage.status_code == 200:
                        print('Status: 200 OK\n')
                    else:
                        self.getRespondMessage()


if len(sys.argv) != 2:
    print('Usage: monitor urls_file')
    sys.exit()

urlsFileName = sys.argv[1]
urls_file = open(urlsFileName, "r")
urls = urls_file.readlines()
    
for urlLink in urls:
    print('URL: ' + urlLink)
    linkPort, linkHost, linkPath = parseUrl(urlLink)
    client = HttpClientSocket(linkHost, linkPort)
    if client.requestMessage(linkPath):
        client.getRespondMessage()

client.clientSocket.close()

