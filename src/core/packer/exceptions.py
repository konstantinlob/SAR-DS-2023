#!/usr/bin/python3
# -*- coding=utf-8 -*-
r"""

"""


__all__ = ['PackerError', 'EmptyBlobError', 'UnexpectedEOFError']


class PackerError(Exception):
    pass


class EmptyBlobError(PackerError):
    pass


class UnexpectedEOFError(PackerError):
    pass
