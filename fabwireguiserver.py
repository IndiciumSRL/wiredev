import logging
import Queue
from threading import Timer

from fabric.api import sudo, settings, task, env, local, get, put, cd
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

import utils

log = logging.getLogger(__name__)


class CodeEvents(FileSystemEventHandler):
    def __init__(self):
        super(CodeEvents, self).__init__()
        self.queue = Queue.Queue()
        self.reloading = False
    def reload(self, event):
        if not self.reloading:
            log.info('Reloading ...')
            self.queue.put(('reload', event))
            self.reloading = True

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            logging.info('Changed %s', event.src_path)
            Timer(2, lambda: self.reload(event)).start()
            return
        logging.info('Not reloading because its not a Python file that has changed.')

def run_tdd():
    '''
    Run unit tests for the project.
    '''
    logging.info('Running unit tests')
    with cd(os.path.join( config.get('vm', 'base_dir') ,'wiregui-server')):
        with settings(warn_only=True):
            result = sudo('/usr/local/bin/py.test -x -vv')
            return result.failed


def reload(event):
    '''
        Reload source code. For reloading, unit tests are mandatory.
    '''
    with settings(warn_only=True):
        utils.growl("File %s changed." % event, "Reloading....")
    logging.info('Reloading the source.')
    if run_tdd():
        with settings(warn_only=True):
            utils.growl("WireGui unit tests FAILED!", "Bummer")
            return
    sudo('supervisorctl restart wiregui')
    with settings(warn_only=True):
        utils.growl("WireGui reloaded.", "Matrix Reloaded")

@task
def run():
    sudo('supervisorctl restart wiregui')
    try:
        event_handler = LoggingEventHandler()
        other_handler = CodeEvents()
        observer = Observer()
        watch = observer.schedule(event_handler, './wiregui-server', recursive=True)
        observer.add_handler_for_watch(other_handler, watch)
        observer.start()
        logging.info('Waiting for events.')
        while True:
            try:
                action,event = other_handler.queue.get(block=True, timeout=0.5)
            except Queue.Empty:
                continue
            if action == 'reload':
                reload(event)
                other_handler.reloading = False
                
                
                


    except KeyboardInterrupt:
        observer.stop()
    observer.join()