import socket
import time
from uuid import uuid1
import urlparse
from threading import Thread
from Queue import Queue
import json
routes = {
          'get'  : {},
          'post' : {}
         }

CONTENT_TYPE = {
                 'html'          : 'text/html',
                 'css'           : 'text/css',
                 'js'            : 'application/javascript',
                 'jpeg'          : 'image/jpeg',
                 'jpg'           : 'image/jpg',
                 'png'           : 'image/png',
                 'gif'           : 'image/gif',
                 'ico'           : 'image/x-icon',
                 'text'          : 'text/plain',
                 'json'          : 'application/json',
               }

sessions = {}
cookies = {}


def add_route(method, path, func):
    routes[method][path] = func


'''
*********************************************************************
Server Functions
'''


def start_server(hostname, port=8080, nworkers=20):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((hostname, port))
        print "server started at port:", port
        sock.listen(3)
        q = Queue(nworkers)
        for i in xrange(nworkers):
            proc = Thread(target=worker_thread, args=(q,))
            proc.daemon = True
            proc.start()
        while True:
            (client_socket, addr) = sock.accept()
            q.put((client_socket, addr))
    except KeyboardInterrupt:
        print "Bye Bye"
    finally:
        sock.close()


def worker_thread(q):
    request = {}
    client_socket, addr = q.get()
    request['socket'] = client_socket
    data = ""
    #Checking valid HTTP Header
    while '\r\n\r\n' not in data:
        buff = client_socket.recv(2048)
        if not buff:
            break
        data += buff
    try:
        header, body = data.split('\r\n\r\n', 1)
    except IndexError and ValueError:
        header = data.split('\r\n\r\n')[0]
        body = ""
    header = header.strip().split('\r\n')
    first = header.pop(0)
    request["method"], request["path"], request["protocol"] = first.split()
    if header:
        request['header'] = header_parser(header)
    if 'Content-Length' in request['header']:
        content_length = int(request['header']['Content-Length'])
        data = body     
        while content_length != len(data):
            buff = client_socket.recv(2048)
            if not buff:
                break
            data += buff
    
        request['body'] = data
    print request
    if request:
        request_handler(request)
    else:
        client_socket.close()


'''
*********************************************************************
Parsers
'''


def header_parser(header_str):
    header={}
    for each_line in header_str:
        key, value  = each_line.split(': ', 1)
        header[key] = value
    try:
        cookies = header['Cookie'].split(';')
        client_cookies = {}
        for cookie in cookies:
            head,body = cookie.strip().split('=', 1)
            client_cookies[head] = body
        header['Cookie'] = client_cookies
    except KeyError:
        header['Cookie'] = ""
    return header


'''
*********************************************************************
Stringify
'''


def response_stringify(response):
    response_string = response['status'] + '\r\n'
    keys = [key for key in response if key not in ['status','content']]
    for key in keys:
        response_string += key + ': ' + response[key] + '\r\n'
    response_string += '\r\n'
    if 'content' in response:
        response_string += response['content'] + '\r\n\r\n'
    return response_string

'''
*********************************************************************
Handler Functions
'''


def request_handler(request):
    response          = {}
    session_handler(request, response)
    method_handler(request,response)
   

def session_handler(request, response):
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies and browser_cookies['sid'] in sessions:
        return
    cookie = str(uuid1())
    response['Set-Cookie'] = 'sid=' + cookie
    sessions[cookie] = {}


def method_handler(request, response):
    handler = METHOD[request['method']]
    handler(request, response)

    
def get_handler(request,response):
    try:
        routes['get'][request['path']](request, response)
    except KeyError:
        static_file_handler(request,response)


def post_handler(request,response):
    try:
        request['content'] = urlparse.parse_qs(request['body'])
        routes['post'][request['path']](request, response)
    except KeyError:
        err_404_hanlder(request, response)


def head_handler(request, response):
    get_handler(request, response)
    response['content'] = ''
    response_handler(request, response)


def static_file_handler(request, response):
    try:
        with open('./public' + request['path'],'r') as fd:
            response['content']  = fd.read() 
        content_type = request['path'].split('.')[-1].lower()
        response['Content-type'] = CONTENT_TYPE[content_type]
        OK_200_handler(request, response)
    except IOError:
        err_404_handler(request,response)


def err_404_handler(request, response):
    response['status'] = "HTTP/1.1 404 Not Found"
    response['content'] = "Content Not Found"
    response['Content-type'] = "text/HTML"
    response_handler(request, response)
             

def OK_200_handler(request, response):
    response['status'] = "HTTP/1.1 200 OK"
    if response['content'] and response['Content-type']:
        response['Content-Length'] = str(len(response['content']))
    response_handler(request, response)


def response_handler(request, response):
    response['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    response['Connection'] = 'close'
    response['Server']     = 'magicserver0.1'
    response_string        = response_stringify(response)
    request['socket'].send(response_string)
    if request['header']['Connection'] != 'keep-alive':
        request['socket'].close()
    else:
        print "Got a live Connection"


def add_session(request, response, content):
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies:
        sid = browser_cookies['sid'] 
        if sid in sessions:
            sessions[sid] = content
    print content


def get_session(request, response):
    print sessions
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies:
        sid = browser_cookies['sid'] 
        if sid in sessions:
            return sessions[sid]


def send_html_handler(request, response, content):
    if content:
        response['content'] = content
        response['Content-type'] = 'text/html'
        OK_200_handler(request, response)
    else:
        err_400_handler(resquest, response)


def send_json_handler(request, response, content):
    if content:
        response['content'] = json.dumps(content)
        response['Content-type'] = 'application/json'
        OK_200_handler(request, response) 
    else:
        err_400_handler(request, response)


def send_html_handler(request, response, content):
    if content:
        response['content'] = content
        response['Content-type'] = 'text/html'
        OK_200_handler(request, response)
    else:
        err_400_handler(resquest, response)


def send_json_handler(request, response, content):
    if content:
        response['content'] = json.dumps(content)
        response['Content-type'] = 'application/json'
        OK_200_handler(request, response) 
    else:
        err_400_handler(request, response)


METHOD  =      {
                 'GET'           : get_handler,
                 'POST'          : post_handler,
                 'HEAD'          : head_handler,
               }

