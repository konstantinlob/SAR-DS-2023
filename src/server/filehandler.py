import os
from pathlib import Path


WATCHED_DIRECTORIES_PATH = "watched"
FILES_ROOT = Path(WATCHED_DIRECTORIES_PATH).absolute()
FILES_ROOT.mkdir(parents=True, exist_ok=True)

def real_path(path: str) -> Path:
    real = (FILES_ROOT / path).absolute()
    if os.path.commonpath([str(FILES_ROOT), real]) != str(FILES_ROOT):
        raise PermissionError("Bad path")
    return real


class FileHandler:
    def handle_client_file_watched(self, src_path: str):
        src_path = real_path(src_path)
        src_path.mkdir(parents=True, exist_ok=True)

    def handle_client_file_created(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.mkdir()
        else:
            src_path.touch()

    def handle_client_file_modified(self, src_path: str, is_directory: bool,
                                    new_content: bytes):  # permissions, atime, mtime, ctime,
        src_path = real_path(src_path)
        if new_content is not None:
            with open(src_path, 'wb') as file:
                file.write(new_content)
        # src_path.chmod(permissions)
        # os.utime(src_path, (atime, mtime))

    def handle_client_file_moved(self, src_path: str, dest_path: str, is_directory: bool):
        src_path = real_path(src_path)
        dist_path = real_path(dest_path)
        src_path.rename(dist_path)

    def handle_client_file_deleted(self, src_path: str, is_directory: bool):
        src_path = real_path(src_path)
        if is_directory:
            src_path.rmdir()
        else:
            src_path.unlink()
