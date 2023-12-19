from pathlib import Path


def parse_path(path: str) -> Path:
    """
    Parse a path string (relative or absolute, beginning with home directory or not) into an absolute Path
    :param path:
    :return: absolute Path
    """

    path_obj = Path(path)

    # Check if the path is relative or contains ~ for the home directory
    if not path_obj.is_absolute() or '~' in str(path_obj):
        # If so, resolve and expanduser to get the absolute path
        return path_obj.expanduser().resolve()
    else:
        return path_obj