from __future__ import unicode_literals, print_function
import random
import string
from StringIO import StringIO
from time import sleep

from collections import Iterable
from fabric.context_managers import settings, cd, shell_env
from fabric.contrib.files import exists
from fabric.operations import sudo, get, put
import six

__all__ = ['config_nginx', 'id_generator', 'add_domain', 'remove_domain', 'get_port_number', 'StreamFilter',
           'run_until_ok', 'load_environment_dict', 'store_environment_dict', 'create_home_folder',
           'create_logs_folder']

nginx_config = """server {{
    listen 80;
    server_name {domain_list};

    location / {{
        include /etc/nginx/proxy_params;
        proxy_pass http://127.0.0.1:{port};
        access_log /home/{project_name}/logs/access.log;
        error_log /home/{project_name}/logs/error.log error;        
    }}
}}
"""
supervisor_config = """[program:{project_name}]
command=forego start
autostart=true
autorestart=true
stopasgroup=true
stdout_logfile=/home/{project_name}/logs/stdout.log
stderr_logfile=/home/{project_name}/logs/stderr.log
user={project_name}
directory=/home/{project_name}/{project_name}
environment=PATH="{PATH}"
"""


def create_home_folder(project_name):
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    sudo('id -u {project_name} &>/dev/null || useradd --shell /bin/false {project_name}'.format(
        project_name=project_name))
    if not exists(home_folder):
        sudo('mkhomedir_helper {project_name}'.format(project_name=project_name))


def create_logs_folder(project_name):
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    with cd(home_folder), settings(sudo_user=project_name), shell_env(HOME=home_folder):
        if not exists('logs'):
            sudo('mkdir logs')

########################


def config_nginx(project_name):
    env_config = load_environment_dict(project_name)
    domain_list = load_domain_list(project_name)
    kwargs = {
        'domain_list': ' '.join(domain_list),
        'port': env_config['PORT'],
        'project_name': project_name
    }
    nginx_content = nginx_config.format(**kwargs)
    put(local_path=StringIO(nginx_content),
        remote_path='/etc/nginx/sites-available/{project_name}'.format(project_name=project_name), use_sudo=True)
    if not exists('/etc/nginx/sites-enabled/{project_name}'.format(project_name=project_name)):
        sudo('ln -s /etc/nginx/sites-available/{project_name} /etc/nginx/sites-enabled/'.format(
            project_name=project_name))
    sudo('service nginx reload')
    run_until_ok('service nginx status')


def config_supervisor(project_name):
    env_config = load_environment_dict(project_name)
    kwargs = {
        'project_name': project_name,
        'PATH': env_config['PATH']
    }
    supervisor_content = supervisor_config.format(**kwargs)
    put(local_path=StringIO(supervisor_content),
        remote_path='/etc/supervisor/conf.d/{project_name}.conf'.format(project_name=project_name), use_sudo=True)
    sudo('supervisorctl reload')
    run_until_ok('supervisorctl status')


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
    port_number = int(port_number) + 1
    put(StringIO(str(port_number)), '.port_number')
    return port_number


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


###################


def load_domain_list(project_name):
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    remote_domain_file_path = '{home_folder}/.domains'.format(home_folder=home_folder)
    if exists(remote_domain_file_path):
        domain_file = StringIO()
        get(remote_domain_file_path, domain_file, use_sudo=True, temp_dir='/tmp')
        return domain_file.getvalue().split()
    return []


def store_domain_list(project_name, domain_list):
    domain_file = StringIO('\n'.join(domain_list))
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    remote_domain_file_path = '{home_folder}/.domains'.format(home_folder=home_folder)
    put(domain_file, '/tmp/{project_name}_domains'.format(project_name=project_name))
    with cd(home_folder), settings(sudo_user=project_name), shell_env(HOME=home_folder):
        sudo('yes | cp /tmp/{project_name}_domains {remote_domain_file_path}'.format(project_name=project_name,
                                                                                     remote_domain_file_path=remote_domain_file_path))
        sudo('chmod 0600 {remote_domain_file_path}'.format(remote_domain_file_path=remote_domain_file_path))


def add_domain(project_name, domain):
    domain_list = load_domain_list(project_name)
    if isinstance(domain, six.string_types):
        domain_list.append(domain)
    else:
        domain_list = domain_list + domain
    store_domain_list(project_name, domain_list)


def remove_domain(project_name, domain):
    domain_list = load_domain_list(project_name)
    if isinstance(domain, six.string_types):
        domain = [domain]
    domain_list = [d for d in domain_list if d not in domain]
    store_domain_list(project_name, domain_list)
