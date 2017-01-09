from __future__ import unicode_literals
from StringIO import StringIO
from fabric.api import task, hosts, sudo, get, settings, shell_env, cd
from fabric.contrib.files import exists, upload_template, put


@task
@hosts('hotels')
def create(username, repo_url):
    """
    Create new project. Usage project.create:<username>,repo_url=<github_url>
    """
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
        sudo('chmod 0600 /home/{username}/{username}/.env'.format(username=username))
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
        sudo('service nginx reload')
        sudo('service nginx status')


@task
@hosts('hotels')
def destroy(username):
    """
    Destroy project. Delete all data and config files. Usage: project.destroy:<username>
    """
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

#@task(default=True)
#def list():
#    run('uname -a')