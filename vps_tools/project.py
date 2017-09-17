from __future__ import unicode_literals, print_function

from StringIO import StringIO
from fabric.api import task, sudo, get, settings, shell_env, cd, hide, execute
from fabric.contrib.files import exists, put, append

from vps_tools.utils import nginx_config, supervisor_config, id_generator, run_until_ok, get_port_number


@task
def create(username, repo_url, no_createdb, no_migrations, base_domain):
    """
    Create new project. Usage project.create:<username>,repo_url=<github_url>
    """
    port_number = get_port_number()
    put(StringIO(str(port_number)), '.port_number')

    env_path = ':'.join(['/usr/local/sbin',
                         '/usr/local/bin',
                         '/usr/sbin',
                         '/usr/bin',
                         '/sbin',
                         '/bin'])

    context = {
        'port': port_number,
        'base_domain': base_domain,
        'username': username,
    }

    if not no_createdb:
        context.update({
            'db_username': id_generator(12),
            'db_password': id_generator(12),
        })
        db_url = 'postgres://{db_username}:{db_password}@localhost:5432/{username}'.format(**context)
        with settings(sudo_user='postgres'):
            sudo('createdb {username}'.format(username=username))
            sudo('psql -c "create user {db_username} with superuser password \'{db_password}\'"'.format(**context))

    home_folder = '/home/{username}'.format(username=username)
    sudo('id -u {username} &>/dev/null || useradd --shell /bin/false {username}'.format(username=username))
    if not exists(home_folder):
        sudo('mkhomedir_helper {username}'.format(username=username))
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):

        if not exists('./{username}'.format(username=username), use_sudo=True):
            sudo('git clone -q {repo_url} {username}'.format(username=username, repo_url=repo_url))

        if exists('/home/{username}/{username}/requirements.txt'.format(username=username)):
            if not exists('./venv', use_sudo=True):
                runtime_file = StringIO()
                runtime = 'python-3.5'
                if exists('/home/{username}/{username}/runtime.txt'.format(username=username)):
                    get('/home/{username}/{username}/runtime.txt'.format(username=username), runtime_file)
                    runtime = runtime_file.getvalue()[:10]
                if runtime == 'python-2.7':
                    sudo('virtualenv venv')
                elif runtime == 'python-3.5':
                    sudo('virtualenv venv --python=/usr/bin/python3.5')

            sudo('./venv/bin/pip install --upgrade pip', pty=False)
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

            env_path = '/home/{username}/venv/bin:'.format(username=username) + env_path
        elif exists('/home/{username}/{username}/package.json'.format(username=username)):
            with cd('/home/{username}/{username}/'.format(username=username)):
                sudo('npm install')
            env_path = '/home/{username}/{username}/node_modules/.bin:'.format(username=username) + env_path

        env = [
            'PORT={port_number}'.format(port_number=port_number),
            'PATH={path}'.format(path=env_path)
        ]
        if not no_createdb:
            env.append('DATABASE_URL={db_url}'.format(db_url=db_url))
        append('./{username}/.env'.format(username=username), env, use_sudo=True)
        if not exists('logs'):
            sudo('mkdir logs')

        if exists('/home/{username}/{username}/requirements.txt'.format(username=username)) and not no_migrations:
            execute(run, username, 'python manage.py collectstatic --noinput')
            if should_sync:
                execute(run, username, 'python manage.py syncdb --noinput')
                if has_south:
                    execute(run, username, 'python manage.py migrate --noinput')
            else:
                execute(run, username, 'python manage.py migrate --noinput')

    context.update({'PATH': env_path})
    nginx_content = nginx_config.format(**context)
    supervisor_content = supervisor_config.format(**context)
    put(local_path=StringIO(nginx_content), remote_path='/etc/nginx/sites-available/{username}'.format(username=username), use_sudo=True)
    put(local_path=StringIO(supervisor_content), remote_path='/etc/supervisor/conf.d/{username}.conf'.format(username=username), use_sudo=True)
    if not exists('/etc/nginx/sites-enabled/{username}'.format(username=username)):
        sudo('ln -s /etc/nginx/sites-available/{username} /etc/nginx/sites-enabled/'.format(username=username))

    sudo('supervisorctl reload')
    run_until_ok('supervisorctl status')

    sudo('service nginx reload')
    run_until_ok('service nginx status')


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
        run_until_ok('supervisorctl status')

    if exists('/var/log/{username}'.format(username=username)):
        sudo('rm -rf /var/log/{username}'.format(username=username))
    if exists(nginx_file_name):
        sudo('rm -rf {}'.format(nginx_file_name))
        sudo('service nginx reload')
        run_until_ok('service nginx status')

    with settings(sudo_user='postgres'):
        sudo('dropdb --if-exists {username}'.format(username=username))
    sudo('deluser --remove-home {}'.format(username))


@task
def deploy(username):
    home_folder = '/home/{username}'.format(username=username)
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        with cd('/home/{username}/{username}/'.format(username=username)):
            sudo('git pull origin')
        if exists('/home/{username}/{username}/requirements.txt'.format(username=username)):
            sudo('./venv/bin/pip install -r ./{username}/requirements.txt'.format(username=username), pty=False)
            execute(run, username, 'python manage.py collectstatic --noinput')
            execute(run, username, 'python manage.py migrate --noinput')
        elif exists('/home/{username}/{username}/package.json'.format(username=username)):
            with cd('/home/{username}/{username}/'.format(username=username)):
                sudo('npm install')
    execute(restart, username)


@task
def run(username, cmd):
    """
    Run command on project environment. Usage: project.run:<username>,cmd='<command>'
    """
    home_folder = '/home/{username}'.format(username=username)
    project_folder = '/home/{username}/{username}'.format(username=username)
    with cd(project_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
        sudo('forego run {cmd}'.format(cmd=cmd))


@task
def restart(username):
    """
    Restart project. Usage: project.restart:<username>
    """
    sudo('supervisorctl restart {username}'.format(username=username))
    run_until_ok('supervisorctl status')


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
        print(i)
