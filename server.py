import socket
import time
from uuid import uuid1
import urlparse
from threading import Thread
from Queue import Queue
import json


ROUTES = {
    'get': {},
    'post': {}
}

CONTENT_TYPE = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpg',
    'png': 'image/png',
    'gif': 'image/gif',
    'ico': 'image/x-icon',
    'text': 'text/plain',
    'json': 'application/json'
}

SESSIONS = {}

def add_route(method, path, func):
    '''ADD ROUTES

    Build ROUTES
    '''
    ROUTES[method][path] = func


#Server Functions


def start_server(hostname, port=8080, nworkers=20):
    '''Start Function

    Initialise socket and listen
   '''
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((hostname, port))
        print "server started at port:", port
        sock.listen(3)
        worker_queue = Queue(nworkers)
        for _ in xrange(nworkers):
            proc = Thread(target=worker_thread, args=(worker_queue,))
            proc.daemon = True
            proc.start()
        while True:
            (client_socket, addr) = sock.accept()
            worker_queue.put((client_socket, addr))
    except KeyboardInterrupt:
        print "Bye Bye"
    finally:
        sock.close()


def worker_thread(worker_queue):
    '''WORKER THREAD

    Accept requests and invoke request handler
    '''
    request = {}
    client_socket, addr = worker_queue.get()
    request['socket'] = client_socket
    request['address'] = addr
    header_str, body_str = get_http_header(request, '')
    if not header_str:
        return
    header_parser(request, header_str)
    if 'Content-Length' in request['header']:
        content_length = int(request['header']['Content-Length'])
        body_str = get_http_body(request, body_str, content_length)
        request['body'] = body_str
    if request:
        request_handler(request)
    else:
        client_socket.close()


#Parsers


def get_http_header(request, data):
    '''HTTP Header evaluator

    Accept HTTP header and evaluate
    '''
    if '\r\n\r\n' in data:
        data_list = data.split('\r\n\r\n', 1)
        header_str = data_list[0]
        body_str = ''
        if len(data_list) > 1:
            body_str = data_list[1]
        return header_str, body_str
    buff = request['socket'].recv(2048)
    if not buff:
        return '', ''
    return get_http_header(request, data+buff)


def get_http_body(request, body_str, content_length):
    '''HTTP Body evaluator

    Accept HTTP Body part, evaluate
    '''
    if content_length == len(body_str):
        return body_str
    buff = request['socket'].recv(2048)
    if not buff:
        return
    return get_http_body(request, body_str+buff, content_length)


def header_parser(request, header_str):
    '''
    HTTP Header Parser
    '''
    header = {}
    header_list = header_str.split('\r\n')
    first = header_list.pop(0)
    request['method'], request['path'], request['protocol'] = first.split()
    for each_line in header_list:
        key, value = each_line.split(': ', 1)
        header[key] = value
    if 'Cookie' in header:
        cookies = header['Cookie'].split(';')
        client_cookies = {}
        for cookie in cookies:
            head, body = cookie.strip().split('=', 1)
            client_cookies[head] = body
        header['Cookie'] = client_cookies
    else:
        header['Cookie'] = ''
    request['header'] = header


#Stringify


def response_stringify(response):
    '''
    Stringify the response object
    '''
    response_string = response['status'] + '\r\n'
    keys = [key for key in response if key not in ['status', 'content']]
    for key in keys:
        response_string += key + ': ' + response[key] + '\r\n'
    response_string += '\r\n'
    if 'content' in response:
        response_string += response['content'] + '\r\n\r\n'
    return response_string

#Handler Functions


def request_handler(request):
    '''Request Handler'''
    response = {}
    session_handler(request, response)
    method_handler(request, response)


def session_handler(request, response):
    '''Session Handler

    Add session ids to SESSION
    '''
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies and browser_cookies['sid'] in SESSIONS:
        return
    cookie = str(uuid1())
    response['Set-Cookie'] = 'sid=' + cookie
    SESSIONS[cookie] = {}


def form_parser(request):
    '''MULTIPART Parser'''
    form = {}
    content_type = request['header']['Content-Type']
    boundary = content_type.split('; ')[1]
    request['boundary'] = '--' + boundary.split('=')[1]
    for content in request['body'].split(request['boundary']):
        form_header_dict = {}
        data = {}
        if not content:
            continue
        form_data = content.split('\r\n\r\n', 1)
        form_header = form_data[0].split('\r\n')
        form_body = ''
        if not form_header:
            continue
        if len(form_data) > 1:
            form_body = form_data[1]
        for each_line in form_header:
            if not each_line or ': ' not in each_line:
                continue
            key, value = each_line.split(': ')
            form_header_dict[key] = value
        if not form_header_dict:
            continue
        for each_item in form_header_dict['Content-Disposition'].split('; '):
            if '=' in each_item:
                name, value = each_item.split('=', 1)
                data[name] = value.strip('"')
                data['body'] = form_body
                form[data['name']] = data
    request['form'] = form


def method_handler(request, response):
    '''METHOD Handler

    call respective method handler
    '''
    handler = METHOD[request['method']]
    handler(request, response)


def get_handler(request, response):
    '''HTTP GET Handler'''
    try:
        ROUTES['get'][request['path']](request, response)
    except KeyError:
        static_file_handler(request, response)


def post_handler(request, response):
    '''HTTP POST Handler'''
    try:
        if 'multipart' in request['header']['Content-Type']:
            form_parser(request)
        request['content'] = urlparse.parse_qs(request['body'])
        ROUTES['post'][request['path']](request, response)
    except KeyError:
        err_404_handler(request, response)


def head_handler(request, response):
    '''HTTP HEAD Handler'''
    get_handler(request, response)
    response['content'] = ''
    response_handler(request, response)


def static_file_handler(request, response):
    '''HTTP Static File Handler'''
    try:
        with open('./public' + request['path'], 'r') as file_descriptor:
            response['content'] = file_descriptor.read()
        content_type = request['path'].split('.')[-1].lower()
        response['Content-type'] = CONTENT_TYPE[content_type]
        ok_200_handler(request, response)
    except IOError:
        err_404_handler(request, response)


def err_404_handler(request, response):
    '''HTTP 404 Handler'''
    response['status'] = "HTTP/1.1 404 Not Found"
    response['content'] = "Content Not Found"
    response['Content-type'] = "text/HTML"
    response_handler(request, response)


def ok_200_handler(request, response):
    '''HTTP 200 Handler'''
    response['status'] = "HTTP/1.1 200 OK"
    if response['content'] and response['Content-type']:
        response['Content-Length'] = str(len(response['content']))
    response_handler(request, response)


def response_handler(request, response):
    '''HTTP response Handler'''
    response['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    response['Connection'] = 'close'
    response['Server'] = 'magicserver0.1'
    response_string = response_stringify(response)
    request['socket'].send(response_string)
    if request['header']['Connection'] != 'keep-alive':
        request['socket'].close()


def add_session(request, content):
    '''ADD SESSION

    Add session id to SESSIONS
    '''
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies:
        sid = browser_cookies['sid']
        if sid in SESSIONS:
            SESSIONS[sid] = content


def get_session(request):
    '''GET SESSION

    Get session id from SESSIONS
    '''
    browser_cookies = request['header']['Cookie']
    if 'sid' in browser_cookies:
        sid = browser_cookies['sid']
        if sid in SESSIONS:
            return SESSIONS[sid]


def send_html_handler(request, response, content):
    '''send_html handler

    Add html content to response
    '''
    if content:
        response['content'] = content
        response['Content-type'] = 'text/html'
        ok_200_handler(request, response)
    else:
        err_404_handler(request, response)


def send_json_handler(request, response, content):
    '''send_json handler

    Add JSON content to response
    '''
    if content:
        response['content'] = json.dumps(content)
        response['Content-type'] = 'application/json'
        ok_200_handler(request, response)
    else:
        err_404_handler(request, response)


METHOD = {
    'GET': get_handler,
    'POST': post_handler,
    'HEAD': head_handler
}
