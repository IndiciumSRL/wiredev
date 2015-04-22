import os

from fabric.api import local, cd, settings, lcd

def clone(url):
    '''
        Clone a repo.
    '''
    path = url.split('/')[-1].split('.')[0]
    if not os.path.exists(path):
        local('git clone %s' % url)

def checkout(path, branch='develop'):
    '''
        Checkout branch of repo
    '''
    with lcd(path):
        with settings(warn_only=True):
            result = local('git rev-parse --verify %s' % branch)
        if result.failed:
            local('git checkout -b %s origin/%s' % (branch, branch))
        else:
            local('git checkout %s' % branch)