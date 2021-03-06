import logging
import Queue
from threading import Timer

from fabric.api import sudo, settings, task, env, local, get, put, cd
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

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

@task
def test_prepare_integration():
    sudo('supervisorctl stop all')
    sudo("su postgres -c 'dropdb wirephone'")
    sudo("su wirephone -c 'createdb wirephone'")
    sudo("su wirephone -c 'psql wirephone < /vagrant/wirerouting/jenkins_wirephone.sql'")
    sudo("su wirephone -c 'alembic -c /etc/wirephone/wirephone.ini upgrade head'")
    sudo('supervisorctl start all')

@task
def test_integration():
    with cd('/vagrant/wirerouting'):
        sudo("su wirephone -c '/usr/local/bin/py.test -v -x --config=/etc/wirephone/wirerouting.ini --bddtestpath=/vagrant/wirerouting/tests/integration_data/'")
@task
def save_integration_db():
    with cd('/vagrant/wirerouting'):
        sudo("su wirephone -c 'pg_dump wirephone' > /vagrant/wirerouting/jenkins_wirephone.sql")        

@task
def run():
    sudo('supervisorctl restart wirephone')
    try:
        event_handler = LoggingEventHandler()
        other_handler = CodeEvents()
        observer = Observer()
        watch = observer.schedule(event_handler, './wirephone', recursive=True)
        observer.add_handler_for_watch(other_handler, watch)
        observer.start()
        logging.info('Waiting for events.')
        while True:
            try:
                action,event = other_handler.queue.get(block=True, timeout=0.5)
            except Queue.Empty:
                continue
            if action == 'reload':
                other_handler.reloading = False
                local("osascript -e 'display notification \"File %s changed.\" with title \"Reloading....\"'" % event)
                logging.info('Reloading the source.')
                sudo('supervisorctl restart wirephone')
                local("osascript -e 'display notification \"Wirephone reloaded.\" with title \"Matrix Reloaded\"'")


    except KeyboardInterrupt:
        observer.stop()
    observer.join()