from __future__ import unicode_literals, print_function
import random
import string
from StringIO import StringIO
from time import sleep

from fabric.context_managers import settings, cd, shell_env
from fabric.contrib.files import exists
from fabric.operations import sudo, get, put
import six

nginx_config = """server {{
    listen 80;
    server_name {username}.{base_domain};

    location / {{
        include /etc/nginx/proxy_params;
        proxy_pass http://127.0.0.1:{port};
        access_log /home/{username}/logs/access.log;
        error_log /home/{username}/logs/error.log error;        
    }}
}}
"""
supervisor_config = """[program:{username}]
command=forego start
autostart=true
autorestart=true
stopasgroup=true
stdout_logfile=/home/{username}/logs/stdout.log
stderr_logfile=/home/{username}/logs/stderr.log
user={username}
directory=/home/{username}/{username}
environment=PATH="{PATH}"
"""


def id_generator(size=6, chars=string.ascii_lowercase):
    return ''.join(random.sample(chars, size))


def run_until_ok(cmd):
    return_code = 1
    with settings(warn_only=True):
        while not return_code == 0:
            sleep(3)
            result = sudo(cmd)
            return_code = result.return_code


def get_port_number():
    if exists('.port_number'):
        port_number_file = StringIO()
        get('.port_number', port_number_file)
        port_number = port_number_file.getvalue()
    else:
        port_number = "8010"
    return int(port_number) + 1


class StreamFilter(object):
    def __init__(self, filters, stream):
        self.stream = stream
        self.filters = filters

    def write(self, data):
        for filter in self.filters:
            data = data.replace(filter, '********')
        self.stream.write(data)
        self.stream.flush()

    def flush(self):
        self.stream.flush()


def load_environment_dict(username):
    env_file = StringIO()
    get('/home/{username}/{username}/.env'.format(username=username), env_file, use_sudo=True, temp_dir='/tmp')
    env_lines = env_file.getvalue().split()
    return dict((line.split('=')[0], line.split('=')[1]) for line in env_lines)


def store_environment_dict(username, env_dict):
    value = ''
    for k, v in six.iteritems(env_dict):
        value += '{}={}\n'.format(k, v)
    env_file = StringIO(value)
    put(env_file, '/tmp/.env')
    home_folder = '/home/{username}'.format(username=username)
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        sudo('yes | cp /tmp/.env /home/{username}/{username}/.env'.format(username=username))
        sudo('chmod 0600 /home/{username}/{username}/.env'.format(username=username))
