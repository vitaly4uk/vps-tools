from __future__ import unicode_literals, print_function

from fabric.decorators import task

from vps_tools.utils import load_domain_list, add_domain, remove_domain, config_nginx


@task()
def list(project_name):
    print('\n'.join(load_domain_list(project_name)))


@task()
def set(project_name, domains):
    add_domain(project_name, domains)
    config_nginx(project_name)


@task()
def unset(project_name, domains):
    remove_domain(project_name, domains)
    config_nginx(project_name)