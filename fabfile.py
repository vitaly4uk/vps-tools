from __future__ import unicode_literals, print_function
from StringIO import StringIO
from fabric.api import local, abort, settings, lcd, get, env, hosts, sudo, reboot
from fabric.contrib.console import prompt
from fabric.context_managers import cd, shell_env
from fabric.contrib.files import exists, upload_template, put

__all__ = ['start_heroku_project', 'version', 'clone_project_template', 'install_requirements', 'start_hmara_project',
           'destroy_hmara_project', 'init_hmara_server']

env.use_ssh_config = True

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
        if [ "$(sudo -u postgres psql -l | grep vagrant | head -n 1 | awk '{print $1}')" != "vagrant" ]
        then
            printf "Create DB vagrant with user vagrant"
            sudo -u postgres createdb vagrant
            set +e
            sudo -u postgres psql -c "create user vagrant with superuser password 'vagrant'"
            if [ $? -ne 0 ]
            then
                sudo -u postgres psql -c "alter user vagrant with superuser password 'vagrant'"
            fi
            set -e
        fi
        cd /vagrant
        if [ ! -f ./fabfile.py ]
        then
            wget -q https://raw.githubusercontent.com/vitaly4uk/vps-tools/master/fabfile.py
        fi
        if [ ! -f ./manage.py ]
        then
            fab clone_project_template
        fi
        fab install_requirements
        honcho run python ./manage.py migrate
        honcho run python ./manage.py createsuperuser
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


def check_vagrant():
    with settings(warn_only=True):
        response = local('vagrant version')
    if response.failed:
        abort('You have to install vagrant first. Please, visit https://www.vagrantup.com/')


def start_heroku_project():
    """
    Start new heroku project from scratch.
    """
    check_heroku()
    check_vagrant()
    set_runtime()
    with open('Vagrantfile', 'w') as f:
        f.write(vagrant_file_content)
    local('vagrant up')


def clone_project_template():
    with lcd('/home/vagrant'):
        local('wget -q https://github.com/vitaly4uk/django-heroku-project-template/archive/master.zip')
        local('unzip ./master.zip')
        local('cp -R /home/vagrant/django-heroku-project-template-master/* /vagrant/')
    with open('.env', 'w') as f:
        f.write('PORT=8000\n')
        f.write('DATABASE_URL=postgres://vagrant:vagrant@localhost:5432/vagrant\n')
    with open('local_settings.py', 'w') as f:
        f.write('DEBUG = True')


def install_requirements():
    with open('requirements.txt', 'r') as f:
        requirements_list = [i.strip() for i in f.readlines()]
    for line in requirements_list:
        local('sudo pip install {}'.format(line))
    response = local('pip freeze', capture=True)
    freeze_list = response.splitlines()
    freeze_dict = dict([item.split('==') for item in freeze_list])
    with open('requirements.txt', 'w') as f:
        f.writelines(['{}=={}\n'.format(i, freeze_dict[i]) for i in requirements_list])


def version():
    """
    Print hmara version.
    """
    print('hmara version 0.0.1')


def init_hmara_server():
    sudo('apt-get update')
    sudo('apt-get install -y postgresql python3.5-dev redis-server git mc htop python-pip python-setuptools')
    sudo('apt-get build-dep -y python3-psycopg2 python-psycopg2 python-imaging')

@hosts('hotels')
def start_hmara_project(username, repo_url):
    if exists('.port_number'):
        port_number_file = StringIO()
        get('.port_number', port_number_file)
        port_number = port_number_file.getvalue()
    else:
        port_number = "8011"
    port_number = int(port_number) + 1
    put(StringIO(str(port_number)), '.port_number')

    home_folder = '/home/{username}'.format(username=username)
    sudo('id -u {username} &>/dev/null || useradd --shell /bin/false {username}'.format(username=username))
    if not exists(home_folder):
        sudo('mkhomedir_helper {username}'.format(username=username))
    with cd(home_folder), settings(sudo_user=username), shell_env(HOME=home_folder):
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
        context = {
            'port': port_number,
            'username': username,
        }
        upload_template('.env.tmpl', destination='/tmp/.env'.format(username=username), context=context, mode=0644,
                        template_dir='./templates')
        sudo('yes | cp /tmp/.env /home/{username}/{username}/.env'.format(username=username))
        sudo('chmod 0300 /home/{username}/{username}/.env'.format(username=username))
        if not exists('logs'):
            sudo('mkdir logs')
        if not exists('templates'):
            sudo('mkdir templates')
        sudo('/home/{username}/venv/bin/python /home/{username}/{username}/manage.py collectstatic --noinput'.format(username=username))
        put('templates/supervisord.conf', '/tmp/supervisord.conf', mode=0644)
        sudo('yes | cp /tmp/supervisord.conf /home/{username}/templates/supervisord.conf'.format(username=username))
    with cd(home_folder):
        upload_template('./templates/nginx.conf', mode=0644, use_sudo=True, context=context,
                        destination='/etc/nginx/sites-available/{username}'.format(username=username))
        sudo('ln -s /etc/nginx/sites-available/{username} /etc/nginx/sites-enabled/'.format(username=username))
        sudo('./venv/bin/honcho export --app-root ./{username} --log /home/{username}/logs --template-dir /home/{username}/templates supervisord /etc/supervisor/conf.d'.format(username=username))
        sudo('supervisorctl reload')
        sudo('supervisorctl status')
        #sudo('service nginx stop')
        #sudo('letsencrypt certonly --standalone -d {server_name} -d {username}.vomelchuk.com'.format(server_name=server_name, username=username))
        sudo('service nginx reload')
        sudo('service nginx status')

@hosts('hotels')
def destroy_hmara_project(username):
    supervisor_file_name = '/etc/supervisor/conf.d/{username}.conf'.format(username=username)
    nginx_file_name = '/etc/nginx/sites-enabled/{username}'.format(username=username)
    if exists(supervisor_file_name):
        sudo('supervisorctl stop {username}:*'.format(username=username))
        sudo('rm {supervisor_file_name}'.format(supervisor_file_name=supervisor_file_name))
        sudo('supervisorctl reload')
        sudo('supervisorctl status')
    if exists('/var/log/{username}'.format(username=username)):
        sudo('rm -rf /var/log/{username}'.format(username=username))
    if exists(nginx_file_name):
        sudo('rm -rf {}'.format(nginx_file_name))
        sudo('service nginx reload')
        sudo('service nginx status')
    sudo('userdel {}'.format(username))
    sudo('rm -rf /home/{}'.format(username))