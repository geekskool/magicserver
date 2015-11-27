# magicserver

Functional web server in Python

## Install

Copy the server.py file to your working folder. Or pip install magicserver, this will install magicserver 0.1 (version) on your system.

## How to use:

Static files have to be enclosed in 'public' directory under root.

/
  public/
    js/
    img/
    css/


To map the dynamic pages, use the function
*server.add_route()* 
which takes 3 parameters

1. HTTP Method.
2. Requested path.
3. Function that would return the dynamic content.

Eg: 
```
def home(request, response):
  return server.send_html_handler(request, response, content)
  
server.add_route('get', '/', home)
```

To start server, use
*server.start_server('ip', port, number_of_workers)*

Eg:

  `server.start_server("localhost", 8080, 20)`

To send html or json data response, use the following functions
*server.send_html_handler()*
*server.send_json_handler()*
which take 3 arguments

1. request
2. response
3. requested html/JSON content

Eg:
```
def function(request, response):
  return server.send_html_handler(request, response, content)
```
