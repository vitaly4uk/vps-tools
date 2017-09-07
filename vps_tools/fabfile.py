from __future__ import unicode_literals, print_function

import os

from fabric.api import env, sudo, task

env.use_ssh_config = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@task
def version():
    """
    Print hmara version.
    """
    with open(os.path.join(BASE_DIR, '__init__.py'), 'r') as version_file:
        _, version = version_file.read().split("=")
    print('hmara version: {}'.format(version[1:-1]))


def init_hmara_server():
    sudo('apt-get update')
    sudo('apt-get install -y postgresql python3.5-dev redis-server git mc htop python-pip python-setuptools awscli')
    sudo('apt-get build-dep -y python3-psycopg2 python-psycopg2 python-imaging')
    sudo('aws configure')
