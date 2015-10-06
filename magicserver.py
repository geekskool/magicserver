import socket
import time
from uuid import uuid1
import urlparse
from threading import Thread
from Queue import Queue

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
            proc = Thread(target=thread_worker, args=(q,))
            proc.daemon = True
            proc.start()
        while True:
            (client_socket, addr) = sock.accept()
            q.put((client_socket, addr))
    except KeyboardInterrupt:
        print "Bye Bye"
    finally:
        sock.close()


def thread_worker(q):
    client_socket, addr = q.get()
    data = ""
    while True:
        buff = client_socket.recv(2048)
        if not buff:
            break
        data += buff
        if isValidHTTP(data):
            break
    if data:
        request_handler(client_socket, data)
    else:
        client_socket.close()


def isValidHTTP(data):
    if '\r\n\r\n' in data:
        try:
            head, body = data.split('\r\n\r\n')
            header = head.strip().split('\r\n')
            header = header_parser(header[1:])
            if 'Content-Length' in header:
                content_length = int(header['Content-Length'])
                if content_length == len(body):
                    return True
            else:
                return True
        except ValueError:
            return False


'''
*********************************************************************
Parsers
'''


def request_parser(message):
    request = {}
    try:
        header, body = message.split('\r\n\r\n')
    except IndexError and ValueError:
        header = message.split('\r\n\r\n')[0]
        body = ""
    header = header.strip().split('\r\n')
    first = header.pop(0)
    request["method"]   = first.split()[0]
    request["path"]     = first.split()[1]
    request["protocol"] = first.split()[2]
    if header:
        request['header']   = header_parser(header)
    else:
        request['header']    = {'Cookie':""}
    request['body']     = body
    return request


def header_parser(message):
    header={}
    for each_line in message:
        key, value  = each_line.split(": ", 1)
        header[key] = value
    try:
        cookies  = header['Cookie'].split(";")
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


def request_handler(client_socket,message):
    response          = {}
    request           = request_parser(message)
    request['socket'] = client_socket
    cookie_handler(request, response)
    method_handler(request,response)
    response_handler(request, response)
    

def cookie_handler(request, response):
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies and browser_cookies['sid'] in cookies:
        return
    cookie                 = str(uuid1())
    response['Set-Cookie'] = 'sid=' + cookie
    cookies[cookie]        = {}


def method_handler(request, response):
    handler = METHOD[request['method']]
    handler(request, response)

    
def get_handler(request,response):
    try:
        cookie = request['header']['Cookie']
        content, content_type    = routes['get'][request['path']](cookie)
        response['status']       = "HTTP/1.1 200 OK"
        response['content']      = content
        response['Content-type'] = CONTENT_TYPE[content_type]
    except KeyError:
        static_file_handler(request,response)


def post_handler(request,response):
    cookie = request['header']['Cookie']
    content = urlparse.parse_qs(request['body'])
    content, content_type = routes['post'][request['path']](content, cookie)
    if not content:
        err_404_handler(request, response)
        return 
    response['status']       = "HTTP/1.1 200 OK"
    response['content']      = content
    response['Content-type'] = CONTENT_TYPE[content_type]


def head_handler(request, response):
    pass


def file_handler(request, response):
    pass


def delete_handler(request, response):
    pass


def static_file_handler(request, response):
    try:
        with open('./public' + request['path'],'r') as fd:
            response['content']  = fd.read() 
        content_type             = request['path'].split('.')[-1].lower()
        response['Content-type'] = CONTENT_TYPE[content_type]
        response['status']       = "HTTP/1.1 200 OK"
    except IOError:
        err_404_handler(request,response)


def err_404_handler(request, response):
    response['status'] = "HTTP/1.1 404 Not Found"
    response['content'] = "Content Not Found"
    response['Content-type'] = "text/HTML"
    

def response_handler(request, response):
    response['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    response['Connection'] = 'close'
    response['Server']     = 'geekskool_magic_server'
    response_string        = response_stringify(response)
    request['socket'].send(response_string)
    request['socket'].close()
   
         
METHOD  =      {
                 'GET'           : get_handler,
                 'POST'          : post_handler,
                 'DELETE'        : delete_handler,
                 'HEAD'          : head_handler,
                 'FILE'          : file_handler,
               }

