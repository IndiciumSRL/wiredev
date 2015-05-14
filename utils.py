import platform

from fabric.api import local

def growl(message, title):
    if platform.system() == 'Darwin':
        local("osascript -e 'display notification \"{}\" with title \"{}\"'".format(message, title))