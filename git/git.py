from fabric.api import local

def clone(url):
    '''
        Clone a repo.
    '''
    local('git clone %s' % url)