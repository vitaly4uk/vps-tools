from __future__ import unicode_literals, print_function

import six
from fabric.api import task, sudo
from fabric.utils import puts
from fabric.colors import green

from .utils import load_environment_dict, store_environment_dict, run_until_ok


@task(default=True)
def list(username):
    """
    List environment variables of project. Usage: config list --name <username>
    """
    env_dict = load_environment_dict(username=username)
    for k, v in six.iteritems(env_dict):
        puts(green('{}={}'.format(k, v)))


@task()
def set(username, kwargs, do_reload=True):
    """
    Set environment variable of project. Usage config set --name <username> --vars [<key>=<value> ...]
    """
    env_dict = load_environment_dict(username=username)
    env_dict.update(kwargs)
    for k, v in six.iteritems(env_dict):
        puts(green('{}={}'.format(k, v)))
    store_environment_dict(username=username, env_dict=env_dict)
    if do_reload:
        sudo('supervisorctl restart {}'.format(username))
        run_until_ok('supervisorctl status')


@task()
def unset(username, args, do_reload=True):
    """
    Unset environment variable of project. Usage config unset --name <username> [<key> ...]
    """
    env_dict = load_environment_dict(username=username)
    for key in args:
        env_dict.pop(key, None)
    for k, v in six.iteritems(env_dict):
        puts(green('{}={}'.format(k, v)))
    store_environment_dict(username=username, env_dict=env_dict)
    if do_reload:
        sudo('supervisorctl restart {}'.format(username))
        run_until_ok('supervisorctl status')