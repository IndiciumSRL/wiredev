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
def run():
    sudo('supervisorctl restart wiremonitor')
    try:
        event_handler = LoggingEventHandler()
        other_handler = CodeEvents()
        observer = Observer()
        watch = observer.schedule(event_handler, './wiremonitorserver', recursive=True)
        observer.add_handler_for_watch(other_handler, watch)
        observer.start()
        logging.info('Waiting for events.')
        while True:
            try:
                action,event = other_handler.queue.get(block=False, timeout=0.5)
            except Queue.Empty:
                continue
            if action == 'reload':
                other_handler.reloading = False
                local("osascript -e 'display notification \"File %s changed.\" with title \"Reloading....\"'" % event)
                logging.info('Reloading the source.')
                sudo('supervisorctl restart wiremonitor')
                local("osascript -e 'display notification \"WireMonitor reloaded.\" with title \"Matrix Reloaded\"'")


    except KeyboardInterrupt:
        observer.stop()
    observer.join()