import server
import requests
import ast
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


def home(request, response):
    data = html_header()
    session_data = server.get_session(request)
    if session_data and 'user' in session_data:
        data += 'Hi '
        user = str(session_data['user'])
        data += user
        blogs = redis_server.smembers('user_blogs' + ':' + user)
    else:
        blogs = redis_server.smembers('all_blogs')
    for blog in blogs:
        data += '<p>'
        data += redis_server.hget(blog, 'title')
        data += '<br>'
        data += redis_server.hget(blog, 'content')
        data += '</p>'
    data += html_tail()
    server.send_html_handler(request, response, data)


def login(request, response):
    with open("./views/login.html", "r") as fd:
        server.send_html_handler(request, response, fd.read())


def verify(request, response):
    url = request['content']['apiUrl'][0]
    header = {'Authorization': ''.join(request['content']['authHeader'])}
    data = requests.get(url, headers=header).text
    data_dict = ast.literal_eval(data)
    phone_num = data_dict['phone_number']
    if redis_server.sismember('all_users', phone_num):
        result = 'success'
    else:
        result = 'failure'
    content = {'status': result, 'user': phone_num}
    server.add_session(request, content)
    server.send_json_handler(request, response, content)


def profile(request, response):
    with open("./views/profile.html", "r") as fd:
        server.send_html_handler(request, response, fd.read())


def update_profile(request, response):
    session_data = server.get_session(request)
    if session_data and 'user' in session_data:
        name = request['content']['name'][0]
        email = request['content']['email'][0]
        redis_key = 'user_profile' + ':' + session_data['user']
        user_details = {'name': name, 'email': email}
        redis_server.hmset(redis_key, user_details)
        return home(request, response)


def write(request, response):
    with open("./views/write.html", "r") as fd:
        server.send_html_handler(request, response, fd.read())


def new_blog(request, response):
    session_data = server.get_session(request)
    if session_data and 'user' in session_data:
        title = request['content']['title'][0]
        blog = request['content']['blog'][0]
        redis_server.incr('counter')
        counter = redis_server.get('counter')
        blog_id = 'blog' + counter
        blog_details = {'title': title, 'content': blog, 'time': time.time()}
        redis_server.hmset(blog_id, blog_details)
        redis_server.sadd('user_blogs' + ':' + session_data['user'], blog_id)
        redis_server.sadd('all_blogs', blog_id)
        redis_server.save()
    return home(request, response)


def admin(request, response):
    with open("./views/admin.html", "r") as fd:
        server.send_html_handler(request, response, fd.read())


def new_user(request, response):
    content = request['content']
    session_data = server.get_session(request)
    if session_data and 'user' in session_data:
        new_user = content['user'][0]
        redis_server.sadd('all_users', new_user)
    return home(request, response)


def build_routes():
    server.add_route('get', '/', home)
    server.add_route('get', '/login', login)
    server.add_route('post', '/verify', verify)
    server.add_route('get', '/profile', profile)
    server.add_route('post', '/update_user', update_profile)
    server.add_route('get', '/write', write)
    server.add_route('post', '/new_blog', new_blog)
    server.add_route('get', '/admin', admin)
    server.add_route('post', '/new_user', new_user)


if __name__ == "__main__":
    port = int(raw_input("PORT>"))
    build_routes()
    server.start_server("127.0.0.1", port, 20)
