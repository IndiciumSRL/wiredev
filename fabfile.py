import logging
import os
from StringIO import StringIO
import Queue

from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from watchdog.observers import Observer
from fabric.api import sudo, settings, task, env, local, get, put, cd

import fabwirephone as wirephone
import fabwiremonitor as wiremonitor
import fabwirerouting as wirerouting
from git import git
from config import config

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def configure_apt_sources():
    sudo("echo 'deb     http://ftp.ccc.uba.ar/pub/linux/debian/debian/     wheezy main contrib non-free\ndeb-src http://ftp.ccc.uba.ar/pub/linux/debian/debian/     wheezy main contrib non-free\ndeb     http://security.debian.org/ wheezy/updates  main contrib non-free\ndeb-src http://security.debian.org/ wheezy/updates  main contrib non-free' > /etc/apt/sources.list")


def configure_apt_proxy():
    with settings(warn_only=True):
        result = sudo('test -e /etc/apt/apt.conf.d/01proxy')
    if result.failed:
        sudo("echo 'Acquire::http::Proxy \"http://%s\";' > /etc/apt/apt.conf.d/01proxy" % config.get('apt', 'proxy_url'))
    else:
        print 'Apt proxy is already configured.'


def configure_wirephone_sources():
    with settings(warn_only=True):
        result = sudo('test -e /etc/apt/sources.list.d/wirephone.list')
    if result.failed:
        sudo('apt-get update')
        sudo('apt-get install -y wget')
        sudo('wget -qO - %s | sudo apt-key add -' % config.get('apt', 'repo_key_url'))
        sudo("echo '%s' > /etc/apt/sources.list.d/wirephone.list" % config.get('apt', 'repo_entry'))
    else:
        print 'Wirephone sources is already configured.'

def install_wirephone_suite():
    dependencies = []
    for line in sudo('apt-cache depends wirephone-suite').split('\n'):
        if 'Depends:' in line:
            if line.split()[1] not in [ m.strip() for m in config.get('apt', 'exclude_modules').split(',') ]:
                dependencies.append(line.split()[1])
            else:
                print 'Excluding', line.split()[1]

    sudo('apt-get -y install %s' % ' '.join(dependencies))
    sudo('supervisorctl reload')

def configure_apt():
    configure_apt_sources()
    configure_apt_proxy()
    configure_wirephone_sources()
    sudo('apt-get update')

@task
def prepare_env():
    configure_apt()
    install_wirephone_suite()
    sudo('apt-get install -y git')
    sudo('apt-get install -y python-pip')
    sudo('pip install pytest')
    sudo('pip install mock')

@task
def provision(project, branch='develop'):
    project_name = project
    git.clone(config.get('repos', project))
    git.checkout(project, branch)
    if config.has_section(project):
        project_name = config.get(project, 'name')
    sudo("perl -i -pe 's/\/usr\/bin\/%s/\/usr\/local\/bin\/%s/g' /etc/supervisor/conf.d/%s.conf" % (project_name, project_name, project_name))
    with cd(os.path.join(config.get('vm', 'base_dir'), project)):
        sudo('python setup.py develop')
    sudo('supervisorctl reload')

@task
def run(project):
    logging.info('Running %s', project)
    module = globals().get(project)
    if module is not None:
        module.run()
    else:
        logging.warning('Project does not have a run command yet.')


@task
def vagrant_config():
    out = local('vagrant ssh-config', capture=True)
    for line in out.split('\n')[1:]:
        key,val = line.strip().split()
        if key == 'HostName':
            env.hosts = ['%s:22' % val]
        elif key == 'User':
            env.user = val
        elif key == 'Port':
            port = val
        elif key == 'IdentityFile':
            env.key_filename = val