import logging
from StringIO import StringIO
import Queue

from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from watchdog.observers import Observer
from fabric.api import sudo, settings, task, env, local, get, put, cd

from git import git
from config import config

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

@task
def configure_apt_sources():
    sudo("echo 'deb     http://ftp.ccc.uba.ar/pub/linux/debian/debian/     wheezy main contrib non-free\ndeb-src http://ftp.ccc.uba.ar/pub/linux/debian/debian/     wheezy main contrib non-free\ndeb     http://security.debian.org/ wheezy/updates  main contrib non-free\ndeb-src http://security.debian.org/ wheezy/updates  main contrib non-free' > /etc/apt/sources.list")

@task
def configure_apt_proxy():
    with settings(warn_only=True):
        result = sudo('test -e /etc/apt/apt.conf.d/01proxy')
    if result.failed:
        sudo("echo 'Acquire::http::Proxy \"http://%s\"'; > /etc/apt/apt.conf.d/01proxy" % config.get('apt', 'proxy_url'))
    else:
        print 'Apt proxy is already configured.'

@task
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

@task
def install_wirephone_suite():
    dependencies = []
    for line in sudo('apt-cache depends wirephone-suite').split('\n'):
        if 'Depends:' in line:
            if line.split()[1] not in config.get('apt', 'exclude_modules'):
                dependencies.append(line.split()[1])
            else:
                print 'Excluding', line.split()[1]

    sudo('apt-get -y install %s' % ' '.join(dependencies))
    sudo('supervisorctl reload')

@task
def configure_apt():
    configure_apt_sources()
    configure_apt_proxy()
    configure_wirephone_sources()
    sudo('apt-get update')

# def clone_repo(repo):
#     git.clone(config.get('repos', repo))