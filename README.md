# magicserver

Functional web server in Python

## Install

pip install magicserver

## Usage

Static files have to be enclosed in the directory, 'public' inside root.

/
  public/
    js/
    img/
    css/


To map dynamic pages, use the function
*magicserver.add_route()* 
which takes 3 parameters

1. HTTP Method
2. Requested path
3. Function that returns dynamic content

Eg: 
```
def home(request, response):
  return '<html><body>Hello World</body></html>', 'html'
  
magicserver.add_route('get', '/', home)
```

To start server, use
*magicserver.start_server('ip', port, number_of_workers)*

Eg:

  `magicserver.start_server("lcalhost", 8080, 20)`
