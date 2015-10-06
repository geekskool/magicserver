import server
import requests
import ast
import json
import redis
import time

redis_server = redis.Redis('localhost')

# Temporary HTML Generator functions
def html_header():
    html = '''\
<html>
<head>
<title>Geekskool Blog</title>
</head>
<body>

'''
    return html

def html_tail():
    html = '''\
</body>
</html>
'''
    return html




def home(cookies):
    try:
        data = html_header()
        if cookies and cookies.has_key('user'):
            data += 'Hi ' 
            user = str(cookies['user'])
            data += user
            blogs = redis_server.smembers('user_blogs' + ':' + user)
        else:
            blogs = redis_server.smembers('all_blogs')
        for blog in blogs:
            data += '<p>'
            data += redis_server.hget(blog, 'title' )
            data += '<br>'
            data += redis_server.hget(blog, 'content' )
            data += '</p>'       
        data += html_tail()
        return (data,'html')
    except IOError:
        return '',''


def login(cookie):
    try:
        with open("./login/login.html", "r") as fd:
            return (fd.read(),'html')
    except IOError:
        return '',''


def verify(content, cookie):
    url         = content['apiUrl'][0]
    header      = {'Authorization': ''.join(content['authHeader'])}
    data        = requests.get(url, headers=header).text
    data_dict   = ast.literal_eval(data)
    phone_num   = data_dict['phone_number']
    return json.dumps({'status':'success', 'user':phone_num}),'json'
    

def update_profile( content, cookie):
    if isinstance(cookie, dict) and cookie.has_key('user'):
        name = content['name'][0]
        email = content['email'][0]
        redis_server.hmset('user_profile' + ':' + cookie['user'], {'name':name, 'email':email})
        print redis_server.hgetall('user_profile' + ':' + cookie['user'])
        return home(cookie)
    else: return '',''


def new_blog( content, cookie):
    if isinstance(cookie, dict) and cookie.has_key('user'):
        title = content['title'][0]
        blog = content['blog'][0]
        redis_server.incr('counter')
        counter = redis_server.get('counter')
        blog_id = 'blog' + counter
        redis_server.hmset(blog_id, {'title': title, 'content': blog, 'time':time.time()})
        redis_server.sadd('user_blogs' + ':' + cookie['user'], blog_id)
        redis_server.sadd('all_blogs', blog_id)
        redis_server.save()
        return home(cookie)

    else: return '',''

def build_routes():
    server.add_route('get','/', home)
    server.add_route('get','/login',login)
    server.add_route('post','/verify',verify)
    server.add_route('post','/update_user',update_profile)
    server.add_route('post','/new_blog',new_blog)

    
if __name__ == "__main__":
    port = int(raw_input("PORT>")) 
    build_routes()
    server.start_server("127.0.0.1", port, 20)
