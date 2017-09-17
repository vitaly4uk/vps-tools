from __future__ import unicode_literals, print_function

import dj_database_url
import sys
from fabric.api import task, sudo, get, settings, shell_env, cd, hide
from fabric.contrib.files import put

from .utils import StreamFilter, load_environment_dict


@task
def dump(username, dump):
    remote_env = load_environment_dict(username)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{username}'.format(username=username)
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder), hide('output'):
        with StreamFilter([database['PASSWORD']], sys.stdout):
            sudo('PGPASSWORD={PASSWORD} pg_dump -Fc --no-acl --no-owner -h localhost -U {USER} {NAME} > latest.dump'.format(**database))
        get('latest.dump', dump, temp_dir='/tmp')


@task
def restore(username, dump):
    remote_env = load_environment_dict(username)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{username}'.format(username=username)
    sudo('supervisorctl stop {username}'.format(username=username))
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        put(dump, '/tmp/latest.dump'.format(username=username))
        with settings(sudo_user='postgres'):
            sudo('dropdb {username}'.format(username=username))
            sudo('createdb {username} -O {db_username}'.format(username=username, db_username=database['USER']))
        with hide('output'), settings(warn_only=True), StreamFilter([database['PASSWORD']], sys.stdout):
            sudo('PGPASSWORD={PASSWORD} pg_restore --clean --no-acl --no-owner -h localhost -U {USER} -d {NAME} /tmp/latest.dump'.format(**database))
    sudo('supervisorctl start {username}'.format(username=username))