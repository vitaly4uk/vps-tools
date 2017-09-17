from __future__ import unicode_literals, print_function
import argparse
import tempfile
import os
import sys
from fabric.api import execute, prompt, env, local

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

from vps_tools.project import create, destroy, run, restart, list_projects, deploy
from vps_tools.config import list, set, unset
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def execute_project(args):
    env.hosts = args.host
    if not args.subcommand == 'list' and args.name is None:
        print('--name is required')
        return
    if args.subcommand == 'create':
        repo_url = args.repo_url
        if repo_url is None:
            repo_url = prompt('Please, input repository url of project:')
        execute(create, args.name, repo_url=repo_url, no_createdb=args.no_createdb,
                no_migrations=args.no_migrations, base_domain=args.base_domain)
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
        execute(deploy, args.name)
    else:
        execute(list_projects)


def execute_config(args):
    env.hosts = args.host
    if args.subcommand == 'list':
        execute(list, args.name)
    elif args.subcommand == 'set':
        kwars = dict((i.split('=')[0], i.split('=')[1]) for i in args.vars)
        execute(set, args.name, kwars)
    elif args.subcommand == 'unset':
        kwars = [i.split('=')[0] for i in args.vars]
        execute(unset, args.name, kwars)


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
    env.hosts = args.host
    if args.subcommand == 'dump':
        execute(dump, args.name, args.dump)
    elif args.subcommand == 'restore':
        execute(restore, args.name, args.dump)


def execute_version(args):
    """
    Show version
    """
    with open(os.path.join(BASE_DIR, '__init__.py'), 'r') as version_file:
        _, version = version_file.read().split("=")
    print('hmara version: {}'.format(version[1:-1]))


def execute_update(args):
    if sys.platform == 'win32':
        print('pip install --upgrade https://github.com/vitaly4uk/vps-tools/archive/master.zip')
    else:
        local('sudo -H pip install --upgrade https://github.com/vitaly4uk/vps-tools/archive/master.zip')


def execute_domain(args):
    pass


def main():
    parser = argparse.ArgumentParser(description='Configure projects on hmara servers.')

    subparser = parser.add_subparsers(title='Available commands', help='List of available comands.')

    parser_project = subparser.add_parser('project', help='#  Manage projects')
    parser_project.add_argument('subcommand', choices=['create', 'deploy', 'destroy', 'run', 'restart', 'list'])
    parser_project.add_argument('--name', help='project name')
    parser_project.add_argument('--repo-url', help='git repository url with project')
    parser_project.add_argument('--cmd', help='', nargs=argparse.REMAINDER)
    parser_project.add_argument('--host', help='host name to run command on [default=hotels]', nargs='+', default='hotels')
    parser_project.add_argument('--no-createdb', help='do not create new database', action='store_true')
    parser_project.add_argument('--no-migrations', help='do not apply migrations', action='store_true')
    parser_project.add_argument('--base-domain', help='base domain. [default=nomax.com.ua]', default='nomax.com.ua')
    parser_project.set_defaults(func=execute_project)

    parser_config = subparser.add_parser('config', help='#  Manage projects config vars')
    parser_config.add_argument('subcommand', choices=['list', 'set', 'unset'])
    parser_config.add_argument('--vars', nargs='+', help='<key>=<value> pairs of vars')
    parser_config.add_argument('--host', help='host name to run command on [default=hotels]', nargs='+', default='hotels')
    parser_config.add_argument('--name', help='project name', required=True)
    parser_config.set_defaults(func=execute_config)

    parser_domain = subparser.add_parser('domain', help='# Manage project domains')
    parser_domain.set_defaults(func=execute_domain)

    parser_service = subparser.add_parser('service', help='#  Manage services')
    parser_service.add_argument('name', choices=['nginx', 'postgresql'], help='service name')
    parser_service.add_argument('service_command',
                                choices=['start', 'stop', 'restart', 'reload', 'force-reload', 'status', 'configtest',
                                         'rotate', 'upgrade'])
    parser_service.add_argument('--host', help='host name to run command on  [default=hotels]', nargs='+', default='hotels')
    parser_service.set_defaults(func=execute_service)

    parser_version = subparser.add_parser('version', help='#  Print hmara version')
    parser_version.set_defaults(func=execute_version)

    parser_update = subparser.add_parser('update', help='#  Update hmara')
    parser_update.set_defaults(func=execute_update)

    parser_pg = subparser.add_parser('pg', help='#  Manage database')
    parser_pg.add_argument('subcommand', choices=['dump', 'restore'])
    parser_pg.add_argument('--name', help='project name', required=True)
    parser_pg.add_argument('--host', help='host name to run command on  [default=hotels]', nargs='+', default='hotels')
    parser_pg.add_argument('--dump', help='dump file name [default=latest.dump]', default='latest.dump')
    parser_pg.set_defaults(func=execute_pg)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
