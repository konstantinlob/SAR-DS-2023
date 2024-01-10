from sys import version_info
def enforce_requirements():
    # needed for typing support
    required_version = (3, 12)

    if version_info < required_version:
        raise ImportError(f"Your Python version {version_info} is not supported. "
                          f"Please use Python {required_version[0]}.{required_version[1]} or higher.")