from __future__ import unicode_literals, print_function
from fabric.api import local, abort, settings
from fabric.contrib.console import prompt


__all__ = ['start_heroku_project', 'hello_world']

vagrant_file_content = """Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.network "forwarded_port", guest: 8000, host: 8000
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "512"
  end
    config.vm.provision "shell" do |s|
    s.inline = <<-SHELL
        set -euo pipefail
        IFS=$'\n\t'
        set +H
        sudo apt-get install python-software-properties
        if [ ! -f /etc/apt/sources.list.d/fkrull-deadsnakes-trusty.list ]
        then
            sudo apt-add-repository ppa:fkrull/deadsnakes
        fi
        if [ ! -f /etc/apt/sources.list.d/fkrull-deadsnakes-python2_7-trusty.list ]
        then
            sudo apt-add-repository ppa:fkrull/deadsnakes-python2.7
        fi
        if [ ! -f /etc/apt/sources.list.d/pgdg.list ]
        then
            sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
            wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
        fi
        sudo apt-get update
        sudo apt-get upgrade -y
        sudo apt-get install -y postgresql redis-server git mc htop python-pip python-setuptools
        sudo apt-get build-dep -y python-psycopg2 python-imaging
        sudo pip install fabric
        cd /vagrant
        fab hello_world
      SHELL
    s.privileged = false
  end
end
"""


def set_runtime():
    response = prompt('Which python version do you prefer (2.7 or 3.5)?', default='2.7')
    if response not in ['2.7', '3.5']:
        abort('Only 2.7 or 3.5 are available')
    with open('runtime.txt', 'w') as f:
        if response == '2.7':
            f.write('python-2.7.12')
        else:
            f.write('python-3.5.2')


def check_heroku():
    with settings(warn_only=True):
        response = local('heroku version')
    if response.failed:
        abort('You have to install heroku first. Please, visit https://devcenter.heroku.com/articles/heroku-command-line')
    print('Heroku have been installed correct.\n')


def start_heroku_project():
    """
    Start new heroku project from scratch.
    """
    check_heroku()
    set_runtime()
    with open('Vagrantfile', 'w') as f:
        f.write(vagrant_file_content)
    local('vagrant up')


def hello_world():
    print('Hello, world!')
