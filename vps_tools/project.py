from __future__ import unicode_literals, print_function

from StringIO import StringIO

import sys
from fabric.api import task, sudo, get, settings, shell_env, cd, hide, execute
from fabric.contrib.files import exists, put, append

from vps_tools.utils import id_generator, run_until_ok, get_port_number, StreamFilter, add_domain, config_nginx, \
    config_supervisor, create_home_folder, create_logs_folder
from vps_tools.config import set as config_set


@task()
def create(username, repo_url, no_createdb, no_migrations, base_domain):
    """
    Create new project. Usage project.create:<username>,repo_url=<github_url>
    """
    home_folder = '/home/{username}'.format(username=username)
    domain_name = '{project_name}.{base_domain}'.format(project_name=username, base_domain=base_domain)

    db_kwargs = {
        'db_username': id_generator(12),
        'db_password': id_generator(12),
        'username': username
    }

    env = ['PORT={port_number}'.format(port_number=get_port_number())]

    create_home_folder(project_name=username)
    create_logs_folder(project_name=username)
    add_domain(project_name=username, domain=domain_name)

    if not no_createdb:
        db_url = 'postgres://{db_username}:{db_password}@localhost:5432/{username}'.format(**db_kwargs)
        env.append('DATABASE_URL={db_url}'.format(db_url=db_url))
        with settings(sudo_user='postgres'), StreamFilter([db_kwargs['db_password']], sys.stdout):
            sudo('psql -c "create user {db_username} with password \'{db_password}\'"'.format(**db_kwargs))
            sudo('createdb {username} -O {db_username}'.format(**db_kwargs))

    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        if not exists('./{username}'.format(username=username), use_sudo=True):
            sudo('git clone -q {repo_url} {username}'.format(username=username, repo_url=repo_url))

    with StreamFilter([db_kwargs['db_password']], sys.stdout):
        append('./{username}/.env'.format(username=username), env, use_sudo=True)

    config_supervisor(project_name=username)
    execute(deploy, username)
    config_nginx(project_name=username)


@task()
def destroy(username):
    """
    Destroy project. Delete all data and config files. Usage: project.destroy:<username>
    """
    supervisor_file_name = '/etc/supervisor/conf.d/{username}.conf'.format(username=username)
    nginx_file_name = '/etc/nginx/sites-enabled/{username}'.format(username=username)
    if exists(nginx_file_name):
        sudo('rm -rf {}'.format(nginx_file_name))
        sudo('service nginx reload')
        run_until_ok('service nginx status')
    if exists(supervisor_file_name):
        sudo('supervisorctl stop {username}'.format(username=username))
        sudo('rm {supervisor_file_name}'.format(supervisor_file_name=supervisor_file_name))
        sudo('supervisorctl reload')
        run_until_ok('supervisorctl status')

    if exists('/var/log/{username}'.format(username=username)):
        sudo('rm -rf /var/log/{username}'.format(username=username))

    with settings(sudo_user='postgres'):
        sudo('dropdb --if-exists {username}'.format(username=username))
    sudo('deluser --remove-home {}'.format(username))


@task()
def deploy(project_name):
    env_path = ':'.join(['/usr/local/sbin',
                         '/usr/local/bin',
                         '/usr/sbin',
                         '/usr/bin',
                         '/sbin',
                         '/bin'])
    home_folder = '/home/{username}'.format(username=project_name)
    project_folder = '/home/{username}/{username}/'.format(username=project_name)
    with cd(home_folder), settings(sudo_user=project_name), shell_env(HOME=home_folder):
        with cd(project_folder):
            sudo('git pull origin')
        if exists('{project_folder}/requirements.txt'.format(project_folder=project_folder)):
            if not exists('./venv', use_sudo=True):
                runtime_file = StringIO()
                runtime = 'python-3.5'
                if exists('{project_folder}/runtime.txt'.format(project_folder=project_folder)):
                    get('{project_folder}/runtime.txt'.format(project_folder=project_folder), runtime_file)
                    runtime = runtime_file.getvalue()[:10]
                if runtime == 'python-2.7':
                    sudo('virtualenv venv')
                elif runtime == 'python-3.5':
                    sudo('virtualenv venv --python=/usr/bin/python3.5')
            sudo('./venv/bin/pip install -r {project_folder}/requirements.txt'.format(project_folder=project_folder), pty=False)
            execute(run, project_name, 'python manage.py collectstatic --noinput')
            should_sync = False
            has_south = False
            requirements_file = StringIO()
            get('{project_folder}/requirements.txt'.format(project_folder=project_folder), requirements_file)
            for line in requirements_file.getvalue().split():
                if '==' not in line:
                    continue
                lib_name, lib_version = line.split('==')
                if lib_name.lower() == 'django':
                    v1, v2, v3 = lib_version.split('.')
                    if int(v2) < 7:
                        should_sync = True
                if lib_name == 'South':
                    has_south = True
            if should_sync:
                execute(run, project_name, 'python manage.py syncdb --noinput')
            if has_south or not should_sync:
                execute(run, project_name, 'python manage.py migrate --noinput')
            env_path = '{home_folder}/venv/bin:'.format(home_folder=home_folder) + env_path
        if exists('{project_folder}/package.json'.format(project_folder=project_folder)):
            if exists('{project_folder}/yarn.lock'):
                with cd(project_folder):
                    sudo('yarn install')
            else:
                with cd(project_folder):
                    sudo('npm install')
            env_path = '{project_folder}/node_modules/.bin:'.format(project_folder=project_folder) + env_path
    execute(config_set, project_name, {'PATH': env_path})


@task()
def run(username, cmd):
    """
    Run command on project environment. Usage: project.run:<username>,cmd='<command>'
    """
    home_folder = '/home/{username}'.format(username=username)
    project_folder = '/home/{username}/{username}'.format(username=username)
    with cd(project_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        sudo('forego run {cmd}'.format(cmd=cmd))


@task()
def restart(project_name):
    """
    Restart project. Usage: project.restart:<username>
    """
    sudo('supervisorctl restart {project_name}'.format(project_name=project_name))
    run_until_ok('supervisorctl status')


@task()
def list_projects():
    """
    Return list of projects
    """
    with cd('/home'), hide('output'):
        result = sudo('for i in $(ls -d */); do echo ${i%%/}; done')
    print('\n'.join(i for i in result.splitlines() if not i == 'ubuntu'))
