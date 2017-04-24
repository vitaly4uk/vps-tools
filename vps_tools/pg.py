from __future__ import unicode_literals, print_function

import dj_database_url
from fabric.api import task, hosts, sudo, get, settings, shell_env, cd, hide
from fabric.contrib.files import exists, upload_template, put, append
import string
import random
from .config import load_environment_dict


def id_generator(size=6, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))


@task
@hosts('hotels')
def dump(username):
    remote_env = load_environment_dict(username)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{username}'.format(username=username)
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        with hide('output'):
            sudo('PGPASSWORD={PASSWORD} pg_dump -Fc --no-acl --no-owner -h localhost -U {USER} {NAME} > latest.dump'.format(**database))
        get('latest.dump', 'latest.dump', temp_dir='/tmp')


@task
@hosts('hotels')
def restore(username):
    remote_env = load_environment_dict(username)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{username}'.format(username=username)
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        put('latest.dump', '/tmp/latest.dump'.format(username=username))
        with hide('output'):
            sudo('PGPASSWORD={PASSWORD} pg_restore --verbose --clean --no-acl --no-owner -h localhost -U {USER} -d {NAME} /tmp/latest.dump'.format(**database))