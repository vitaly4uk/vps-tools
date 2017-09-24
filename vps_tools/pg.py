from __future__ import unicode_literals, print_function

import dj_database_url
import sys
from fabric.api import task, sudo, get, settings, shell_env, cd, hide
from fabric.contrib.files import put

from .utils import StreamFilter, load_environment_dict


@task
def dump(project_name, dump):
    remote_env = load_environment_dict(project_name)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    with cd(home_folder), settings(sudo_user='postgres'), shell_env(HOME=home_folder), hide('output'):
        with StreamFilter([database['PASSWORD']], sys.stdout):
            sudo('PGPASSWORD={PASSWORD} pg_dump -Fc --no-acl --no-owner {NAME} > latest.dump'.format(**database))
        get('latest.dump', dump, temp_dir='/tmp')


@task
def restore(project_name, dump):
    remote_env = load_environment_dict(project_name)
    database = dj_database_url.parse(remote_env['DATABASE_URL'])
    home_folder = '/home/{project_name}'.format(project_name=project_name)
    sudo('supervisorctl stop {project_name}'.format(project_name=project_name))
    with cd(home_folder), settings(sudo_user='postgres'), shell_env(HOME=home_folder):
        put(dump, '/tmp/{project_name}.dump'.format(project_name=project_name))
        with settings(sudo_user='postgres'):
            sudo('dropdb --if-exists -h {HOST} -p {PORT} {NAME}'.format(**database))
            sudo('createdb {NAME} -O {USER} -h {HOST} -p {PORT}'.format(**database))
        with hide('output'), settings(warn_only=True), StreamFilter([database['PASSWORD']], sys.stdout):
            sudo('PGPASSWORD={PASSWORD} pg_restore --clean --no-acl --no-owner -d {NAME} /tmp/latest.dump'.format(**database))
    sudo('supervisorctl start {project_name}'.format(project_name=project_name))