from __future__ import unicode_literals
from fabric.api import task, hosts, sudo


@task(default=True)
@hosts('hotels')
def status():
    """
    Show sttus of all services
    """
    sudo('service postgresql status')
    sudo('service nginx status')
    sudo('supervisorctl status')


@task
@hosts('hotels')
def nginx(command):
    """
    Usage: service.nginx:{start|stop|restart|reload|force-reload|status|configtest|rotate|upgrade}
    """
    if command in ['start', 'stop', 'restart', 'reload', 'force-reload', 'status', 'configtest', 'rotate', 'upgrade']:
        sudo('service nginx {}'.format(command))


@task
@hosts('hotels')
def postgresql(command):
    """
    Usage: service.postgresql:{start|stop|restart|reload|force-reload|status}
    """
    if command in ['start', 'stop', 'restart', 'reload', 'force-reload', 'status']:
        sudo('service postgresql {}'.format(command))