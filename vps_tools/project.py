from __future__ import unicode_literals

from StringIO import StringIO
from time import sleep

from fabric.api import task, hosts, sudo, get, settings, shell_env, cd, hide
from fabric.contrib.files import exists, upload_template, put, append
import string
import random


def id_generator(size=6, chars=string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))


@task
def create(username, repo_url):
    """
    Create new project. Usage project.create:<username>,repo_url=<github_url>
    """
    if exists('.port_number'):
        port_number_file = StringIO()
        get('.port_number', port_number_file)
        port_number = port_number_file.getvalue()
    else:
        port_number = "8010"
    port_number = int(port_number) + 1
    put(StringIO(str(port_number)), '.port_number')

    context = {
        'port': port_number,
        'username': username,
        'db_username': id_generator(12),
        'db_password': id_generator(12),
    }

    with settings(sudo_user='postgres'):
        sudo('createdb {username}'.format(username=username))
        sudo('psql -c "create user {db_username} with superuser password \'{db_password}\'"'.format(**context))

    home_folder = '/home/{username}'.format(username=username)
    sudo('id -u {username} &>/dev/null || useradd --shell /bin/false {username}'.format(username=username))
    if not exists(home_folder):
        sudo('mkhomedir_helper {username}'.format(username=username))
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        remote_path = sudo('echo $PATH')
        context.update({'ENV_PATH': remote_path})
        if not exists('./{username}'.format(username=username), use_sudo=True):
            sudo('git clone -q {repo_url} {username}'.format(username=username, repo_url=repo_url))
        if not exists('./venv', use_sudo=True):
            runtime_file = StringIO()
            get('/home/{username}/{username}/runtime.txt'.format(username=username), runtime_file)
            runtime = runtime_file.getvalue()[:10]
            if runtime == 'python-2.7':
                sudo('virtualenv venv')
            elif runtime == 'python-3.5':
                sudo('virtualenv venv --python=/usr/bin/python3.5')

        sudo('./venv/bin/pip install --upgrade pip', pty=False)
        sudo('./venv/bin/pip install honcho[export]', pty=False)
        sudo('./venv/bin/pip install -r ./{username}/requirements.txt'.format(username=username), pty=False)

        should_sync = False
        has_south = False
        requirements_file = StringIO()
        get('/home/{username}/{username}/requirements.txt'.format(username=username), requirements_file)
        for line in requirements_file.getvalue().split():
            if '==' not in line:
                continue
            lib_name, lib_version = line.split('==')
            if lib_name == 'Django':
                v1, v2, v3 = lib_version.split('.')
                if int(v2) < 7:
                    should_sync = True
            if lib_name == 'South':
                has_south = True

        db_url = 'postgres://{db_username}:{db_password}@localhost:5432/{username}'.format(**context)
        env = [
            'PORT={port_number}'.format(port_number=port_number),
            'DATABASE_URL={db_url}'.format(db_url=db_url),
            'PATH=/home/{username}/venv/bin:{path}'.format(username=username, path=remote_path)
        ]
        append('./{username}/.env'.format(username=username), env, use_sudo=True)
        if not exists('logs'):
            sudo('mkdir logs')

        with cd('{username}'.format(username=username)):
            sudo('/home/{username}/venv/bin/honcho run python ./manage.py collectstatic --noinput'.format(username=username))
            if should_sync:
                sudo('/home/{username}/venv/bin/honcho run python ./manage.py syncdb --noinput'.format(username=username))
                if has_south:
                    sudo('/home/{username}/venv/bin/honcho run python ./manage.py migrate --noinput'.format(username=username))
            else:
                sudo('/home/{username}/venv/bin/honcho run python ./manage.py migrate --noinput'.format(username=username))

    upload_template('/var/lib/vps_tools/nginx.conf', mode=0644, use_sudo=True, context=context,
                    destination='/etc/nginx/sites-available/{username}'.format(username=username))
    if not exists('/etc/nginx/sites-enabled/{username}'.format(username=username)):
        sudo('ln -s /etc/nginx/sites-available/{username} /etc/nginx/sites-enabled/'.format(username=username))
    upload_template('/var/lib/vps_tools/supervisord.conf', mode=0644, use_sudo=True, context=context,
                    destination='/etc/supervisor/conf.d/{username}.conf'.format(username=username))
    sudo('supervisorctl reload')
    return_code = 1
    with settings(warn_only=True):
        while not return_code == 0:
            sleep(3)
            print('Try to get supervisor status')
            result = sudo('supervisorctl status')
            return_code = result.return_code
    sudo('service nginx reload')
    return_code = 1
    with settings(warn_only=True):
        while not return_code == 0:
            sleep(3)
            print('Try to get nginx status')
            result = sudo('service nginx status')
            return_code = result.return_code

@task
def destroy(username):
    """
    Destroy project. Delete all data and config files. Usage: project.destroy:<username>
    """
    supervisor_file_name = '/etc/supervisor/conf.d/{username}.conf'.format(username=username)
    nginx_file_name = '/etc/nginx/sites-enabled/{username}'.format(username=username)
    if exists(supervisor_file_name):
        sudo('supervisorctl stop {username}'.format(username=username))
        sudo('rm {supervisor_file_name}'.format(supervisor_file_name=supervisor_file_name))
        sudo('supervisorctl reload')
        return_code = 1
        with settings(warn_only=True):
            while not return_code == 0:
                sleep(3)
                print('Try to get supervisor status')
                result = sudo('supervisorctl status')
                return_code = result.return_code
    if exists('/var/log/{username}'.format(username=username)):
        sudo('rm -rf /var/log/{username}'.format(username=username))
    if exists(nginx_file_name):
        sudo('rm -rf {}'.format(nginx_file_name))
        sudo('service nginx reload')
        return_code = 1
        with settings(warn_only=True):
            while not return_code == 0:
                sleep(3)
                print('Try to get nginx status')
                result = sudo('service nginx status')
                return_code = result.return_code
    with settings(sudo_user='postgres'):
        sudo('dropdb --if-exists {username}'.format(username=username))
    sudo('deluser --remove-home {}'.format(username))


@task
def run(username, cmd):
    """
    Run command on project environment. Usage: project.run:<username>,cmd='<command>'
    """
    home_folder = '/home/{username}'.format(username=username)
    with cd('/home/{username}/{username}'.format(username=username)), settings(sudo_user=username), shell_env(HOME=home_folder):
        sudo('/home/{username}/venv/bin/honcho run {cmd}'.format(username=username, cmd=cmd))


@task
def restart(username):
    """
    Restart project. Usage: project.restart:<username>
    """
    sudo('supervisorctl restart {username}'.format(username=username))


@task
def list_projects():
    """
    Return list of projects
    """
    with cd('/home'):
        with hide('output'):
            result = sudo('for i in $(ls -d */); do echo ${i%%/}; done')
    for i in result.splitlines():
        if i == 'ubuntu':
            continue
        print i
