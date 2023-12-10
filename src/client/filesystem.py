import logging
import os
import typing as t
from pathlib import Path

import watchdog.events as evt
from watchdog.events import FileSystemEventHandler

from core.commands import Command


class ClientFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, send, path):
        self.send = send
        self.path = Path(path)

    def get_relative(self, path: str) -> str:
        return os.path.join(
            self.path.name,
            os.path.relpath(path, self.path)
        )

    def on_any_event(self, event):
        logging.debug(f"Watchdog: {event!r}")

    def on_created(self, event: t.Union[evt.DirCreatedEvent, evt.FileCreatedEvent]):
        self.send(
            command=Command.CREATED,
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_deleted(self, event: t.Union[evt.DirDeletedEvent, evt.FileDeletedEvent]):
        self.send(
            command=Command.DELETED,
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
            )
        )

    def on_moved(self, event: t.Union[evt.DirMovedEvent, evt.FileMovedEvent]):
        self.send(
            command=Command.MOVED,
            body=dict(
                src_path=self.get_relative(event.src_path),
                dest_path=self.get_relative(event.dest_path),
                is_directory=event.is_directory,
            )
        )

    def on_modified(self, event: t.Union[evt.DirModifiedEvent, evt.FileModifiedEvent]):
        fp = Path(event.src_path)
        # stat = os.stat(event.src_path)
        # permissions = stat.st_mode & 0o777
        self.send(
            command=Command.MODIFIED,
            body=dict(
                src_path=self.get_relative(event.src_path),
                is_directory=event.is_directory,
                # permissions=permissions,
                # atime=stat.st_atime,
                # mtime=stat.st_mtime,
                # ctime=stat.st_ctime,
                new_content=None if event.is_directory or not fp.is_file() else fp.read_bytes(),
            )
        )
