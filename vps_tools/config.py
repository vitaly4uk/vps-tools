from __future__ import unicode_literals, print_function
from StringIO import StringIO
import six
from fabric.api import task, hosts, sudo, settings, cd, shell_env, get
from fabric.contrib.files import put


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


@task(default=True)
@hosts('hotels')
def list(username):
    """
    List environment variables of project. Usage: config.list:<username>
    """
    env_dict = load_environment_dict(username=username)
    for k, v in six.iteritems(env_dict):
        print('{}={}'.format(k, v))


@task
@hosts('hotels')
def set(username, **kwargs):
    """
    Set environment variable of project. Usage config.set:<username>[,<key>=<value>, ...]
    """
    env_dict = load_environment_dict(username=username)
    env_dict.update(kwargs)
    for k, v in six.iteritems(env_dict):
        print('{}={}'.format(k, v))
    store_environment_dict(username=username, env_dict=env_dict)
    sudo('supervisorctl restart {}'.format(username))
    sudo('supervisorctl status')