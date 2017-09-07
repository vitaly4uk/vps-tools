from __future__ import unicode_literals, print_function
import project, service, config

from StringIO import StringIO
from fabric.api import local, abort, settings, lcd, get, env, hosts, sudo, reboot, task
from fabric.contrib.console import prompt
from fabric.context_managers import cd, shell_env
from fabric.contrib.files import exists, upload_template, put
import os
import sys
import pkg_resources
env.use_ssh_config = True



def set_runtime():
    response = prompt('Which python version do you prefer (2.7 or 3.5)?', default='2.7')
    if response not in ['2.7', '3.5']:
        abort('Only 2.7 or 3.5 are available')
    with open('runtime.txt', 'w') as f:
        if response == '2.7':
            f.write('python-2.7.12')
        else:
            f.write('python-3.5.2')


def check_heroku():
    with settings(warn_only=True):
        response = local('heroku version')
    if response.failed:
        abort(
            'You have to install heroku first. Please, visit https://devcenter.heroku.com/articles/heroku-command-line')
    print('Heroku have been installed correct.\n')


def check_vagrant():
    with settings(warn_only=True):
        response = local('vagrant version')
    if response.failed:
        abort('You have to install vagrant first. Please, visit https://www.vagrantup.com/')


def start_heroku_project():
    """
    Start new heroku project from scratch.
    """
    check_heroku()
    check_vagrant()
    set_runtime()
    with open('Vagrantfile', 'w') as f:
        f.write(vagrant_file_content)
    local('vagrant up')


def clone_project_template():
    with lcd('/home/vagrant'):
        local('wget -q https://github.com/vitaly4uk/django-heroku-project-template/archive/master.zip')
        local('unzip ./master.zip')
        local('cp -R /home/vagrant/django-heroku-project-template-master/* /vagrant/')
    with open('.env', 'w') as f:
        f.write('PORT=8000\n')
        f.write('DATABASE_URL=postgres://vagrant:vagrant@localhost:5432/vagrant\n')
    with open('local_settings.py', 'w') as f:
        f.write('DEBUG = True')


def install_requirements():
    with open('requirements.txt', 'r') as f:
        requirements_list = [i.strip() for i in f.readlines()]
    for line in requirements_list:
        local('sudo pip install {}'.format(line))
    response = local('pip freeze', capture=True)
    freeze_list = response.splitlines()
    freeze_dict = dict([item.split('==') for item in freeze_list])
    with open('requirements.txt', 'w') as f:
        f.writelines(['{}=={}\n'.format(i, freeze_dict[i]) for i in requirements_list])


@task
def version():
    """
    Print hmara version.
    """
    if pkg_resources.resource_exists('vps_tools', 'VERSION'):
        version_path = pkg_resources.resource_filename('vps_tools', 'VERSION')
    else:
        if os.path.isfile('./VERSION'):
            version_path = './VERSION'
        else:
            version_path = os.path.join(sys.prefix, 'vps_tools', 'VERSION')
    print(version_path)
    with open(version_path, 'r') as version_file:
        print('hmara version {}'.format(version_file.read()))
    pkg_resources.cleanup_resources()


def init_hmara_server():
    sudo('apt-get update')
    sudo('apt-get install -y postgresql python3.5-dev redis-server git mc htop python-pip python-setuptools awscli')
    sudo('apt-get build-dep -y python3-psycopg2 python-psycopg2 python-imaging')
    sudo('aws configure')
