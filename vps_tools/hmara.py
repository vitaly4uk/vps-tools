#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import argparse
import tempfile
import os
from fabric.api import execute, prompt, env, local

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

from vps_tools.fabfile import version
from vps_tools.project import create, destroy, run, restart, list_projects
from vps_tools.config import list, set
from vps_tools.service import nginx, postgresql
from vps_tools.pg import dump, restore
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=os.path.join(tempfile.gettempdir(), 'hmara.log'),
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

env.use_ssh_config = True

env.hosts = ['hotels']

SQS_URL = 'https://sqs.us-east-1.amazonaws.com/455994469874/hmara'


def execute_project(args):
    if args.host:
        env.hosts = args.host
    if not args.subcommand == 'list' and args.name is None:
        print('--name is required')
        return
    if args.subcommand == 'create':
        repo_url = args.repo_url
        if repo_url is None:
            repo_url = prompt('Please, input repository url of project:')
        execute(create, args.name, repo_url=repo_url)
    elif args.subcommand == 'destroy':
        execute(destroy, args.name)
    elif args.subcommand == 'run':
        if args.cmd is None:
            cmd = prompt('Please, input command:')
        else:
            cmd = ' '.join(args.cmd)
        execute(run, args.name, cmd)
    elif args.subcommand == 'restart':
        execute(restart, args.name)
    elif args.subcommand == 'deploy':
        execute(run, args.name, 'git pull origin')
        execute(run, args.name, 'pip install --upgrade -r requirements.txt')
        execute(run, args.name, 'python ./manage.py collectstatic --noinput')
        execute(run, args.name, 'python ./manage.py migrate --noinput')
        execute(restart, args.name)
    else:
        execute(list_projects)


def execute_config(args):
    if args.host:
        env.hosts = args.host
    if args.subcommand == 'list':
        execute(list, args.name)
    elif args.subcommand == 'set':
        kwars = dict((i.split('=')[0], i.split('=')[1]) for i in args.vars)
        execute(set, args.name, **kwars)


def execute_service(args):
    """
    Service commands
    """
    if args.host:
        env.hosts = args.host
    if args.name == 'nginx':
        execute(nginx, args.service_command)
    elif args.name == 'postgresql':
        execute(postgresql, args.service_command)


def execute_pg(args):
    """Database commands."""
    if args.host:
        env.hosts = args.host
    if args.subcommand == 'dump':
        execute(dump, args.name)
    elif args.subcommand == 'restore':
        execute(restore, args.name)


def execute_version(args):
    """
    Show version
    """
    execute(version)


def execute_update(args):
    local('sudo -H pip install --upgrade https://github.com/vitaly4uk/vps-tools/archive/master.zip')


def execute_domain(args):
    pass


def default_command():
    print('Default')


def main():
    parser = argparse.ArgumentParser(description='Configure projects on hmara servers.')

    subparser = parser.add_subparsers(title='Available commands', help='List of available comands.')

    parser_project = subparser.add_parser('project', help='#  Manage projects')
    parser_project.add_argument('subcommand', choices=['create', 'deploy', 'destroy', 'run', 'restart', 'list'])
    parser_project.add_argument('--name', help='project name')
    parser_project.add_argument('--repo_url', help='git repository url with project')
    parser_project.add_argument('--cmd', help='', nargs=argparse.REMAINDER)
    parser_project.add_argument('--host', help='host name to run command on', nargs='+')
    parser_project.set_defaults(func=execute_project)

    parser_config = subparser.add_parser('config', help='#  Manage projects config vars')
    parser_config.add_argument('subcommand', choices=['list', 'set', 'unset'])
    parser_config.add_argument('--vars', nargs='+', help='<key>=<value> pairs of vars')
    parser_config.add_argument('--host', help='host name to run command on', nargs='+')
    parser_config.add_argument('name')
    parser_config.set_defaults(func=execute_config)

    parser_domain = subparser.add_parser('domain', help='# Manage project domains')
    parser_domain.set_defaults(func=execute_domain)

    parser_service = subparser.add_parser('service', help='#  Manage services')
    parser_service.add_argument('name', choices=['nginx', 'postgresql'], help='service name')
    parser_service.add_argument('service_command',
                                choices=['start', 'stop', 'restart', 'reload', 'force-reload', 'status', 'configtest',
                                         'rotate', 'upgrade'])
    parser_service.add_argument('--host', help='host name to run command on', nargs='+')
    parser_service.set_defaults(func=execute_service)

    parser_version = subparser.add_parser('version', help='#  Print hmara version')
    parser_version.set_defaults(func=execute_version)

    parser_update = subparser.add_parser('update', help='#  Update hmara')
    parser_update.set_defaults(func=execute_update)

    parser_pg = subparser.add_parser('pg', help='#  Manage database')
    parser_pg.add_argument('subcommand', choices=['dump', 'restore'])
    parser_pg.add_argument('name', help='project name')
    parser_pg.add_argument('--host', help='host name to run command on', nargs='+')
    parser_pg.set_defaults(func=execute_pg)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()