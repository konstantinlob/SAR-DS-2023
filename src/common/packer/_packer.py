#!/usr/bin/python3
# -*- coding=utf-8 -*-
r"""
Structure of head byte
+------------+--------------------------+--------------------------------------------------------+
|   1 2 3    |            4             |                        5 6 7 8                         |
+------------+--------------------------+--------------------------------------------------------+
| Identifier | next is n bytes for size | size of content if not 4 else number of bytes for size |
+------------+--------------------------+--------------------------------------------------------+

"""
import enum
import io
import math
import struct
import typing as t

from .exceptions import *

PACKED = t.Tuple[int, bytes]


class Identifier(enum.IntEnum):
    NULL = 0
    BINARY = 1
    STRING = 2
    BOOLEAN = 3
    INTEGER = 4
    NUMBER = 5
    MAPPING = 6
    ITERABLE = 7


# mains


def pack(o: t.Any):
    identifier = TYPE2IDENTIFIER[type(o)]
    packer = IDENTIFIER2PACKER.get(identifier)
    if packer is None:
        raise PackerError(f"Unknown Type {type(o).__name__}")
    size, packed = packer(o)
    return _pack_head(identifier, size) + packed


def unpack(stream: t.Union[bytes, t.BinaryIO]):
    if isinstance(stream, bytes):
        stream = io.BytesIO(stream)
    identifier, size = _unpack_head(stream)
    unpacker = IDENTIFIER2UNPACKER.get(identifier)
    if unpacker is None:
        raise PackerError(f"Unknown Identifier")
    return unpacker(size, stream)


# helper


def _pack_head(identifier: Identifier, size: int) -> bytes:
    if size < 16:
        return int.to_bytes((identifier << 5) | 0b00010000 | size, 1, byteorder='big', signed=False)
    else:
        n_bytes = math.ceil(math.log(size) / math.log(256))
        size_bytes = int.to_bytes(size, n_bytes, byteorder='big', signed=False)
        head = int.to_bytes((identifier << 5) | len(size_bytes), 1, byteorder='big', signed=False)
        return head + size_bytes


def _unpack_head(stream: io.BytesIO) -> t.Tuple[Identifier, int]:
    head = stream.read(1)
    if not head:
        raise UnexpectedEOFError()
    num = int.from_bytes(head, byteorder="big", signed=False)
    identifier = (num & 0b11100000) >> 5
    small = num & 0b00010000
    if small:
        size = num & 0b00001111
        return Identifier(identifier), size
    else:
        length = num & 0b00001111
        size_bytes = _read_n(stream=stream, size=length)
        size = int.from_bytes(size_bytes, byteorder="big", signed=False)
        return Identifier(identifier), size


def _read_n(stream: t.BinaryIO, size: int) -> bytes:
    blob = stream.read(size)
    if len(blob) != size:
        raise UnexpectedEOFError("unexpected EOF")
    return blob


# packer / unpacker


def _pack_null(_: None) -> PACKED:
    return 0, b''


def _unpack_null(size: int, _: t.BinaryIO) -> None:
    if size != 0:
        raise PackerError("Bad null value")
    return None


def _pack_binary(b: bytes) -> PACKED:
    return len(b), b


def _unpack_binary(size: int, stream: io.BytesIO) -> bytes:
    return _read_n(stream=stream, size=size)


def _pack_string(s: str) -> PACKED:
    b = s.encode()
    return len(b), b


def _unpack_string(size: int, stream: io.BytesIO) -> str:
    return _read_n(stream=stream, size=size).decode()


def _pack_boolean(b: bool) -> PACKED:
    return 1 if b else 0, b''


def _unpack_boolean(size: int, _: io.BytesIO) -> bool:
    if size == 0:
        return False
    elif size == 1:
        return True
    else:
        raise PackerError("Bad Boolean value")


def _pack_integer(i: int) -> PACKED:
    if i == 0:
        return 0, b''
    signed = i < 0
    i = abs(i)
    n_bytes = max(1, math.ceil(math.log(i) / math.log(256)))
    number = int.to_bytes(i, n_bytes, byteorder='big', signed=False)
    return (n_bytes << 1) | signed, number


def _unpack_integer(size: int, stream: io.BytesIO) -> int:
    if size == 0:
        return 0
    signed = size & 0b1
    size >>= 1
    blob = _read_n(stream=stream, size=size)
    number = int.from_bytes(blob, byteorder='big', signed=False)
    return -number if signed else number


def _pack_number(n: float) -> PACKED:
    return struct.calcsize("!f"), struct.pack("!f", n)


def _unpack_number(size: int, stream: io.BytesIO) -> float:
    return struct.unpack("!f", _read_n(stream=stream, size=size))[0]


def _pack_mapping(m: dict) -> PACKED:
    parts: t.List[bytes] = []
    size = 0
    for key, value in m.items():
        size += 1
        parts.append(pack(key))
        parts.append(pack(value))
    return size, b''.join(parts)


def _unpack_mapping(size: int, stream: io.BytesIO) -> dict:
    obj = dict()
    for _ in range(size):
        key = unpack(stream)
        value = unpack(stream)
        obj[key] = value
    return obj


def _pack_iterable(i) -> PACKED:
    parts: t.List[bytes] = []
    size = 0
    for element in i:
        size += 1
        parts.append(pack(element))
    return size, b''.join(parts)


def _unpack_iterable(size: int, stream: io.BytesIO) -> list:
    return [
        unpack(stream)
        for _ in range(size)
    ]


TYPE2IDENTIFIER = {
    type(None): Identifier.NULL,
    bytes: Identifier.BINARY,
    str: Identifier.STRING,
    bool: Identifier.BOOLEAN,
    int: Identifier.INTEGER,
    float: Identifier.NUMBER,
    dict: Identifier.MAPPING,
    tuple: Identifier.ITERABLE,
    list: Identifier.ITERABLE,
}
IDENTIFIER2PACKER = {
    Identifier.NULL: _pack_null,
    Identifier.BINARY: _pack_binary,
    Identifier.STRING: _pack_string,
    Identifier.BOOLEAN: _pack_boolean,
    Identifier.INTEGER: _pack_integer,
    Identifier.NUMBER: _pack_number,
    Identifier.MAPPING: _pack_mapping,
    Identifier.ITERABLE: _pack_iterable,
}
IDENTIFIER2UNPACKER = {
    Identifier.NULL: _unpack_null,
    Identifier.BINARY: _unpack_binary,
    Identifier.STRING: _unpack_string,
    Identifier.BOOLEAN: _unpack_boolean,
    Identifier.INTEGER: _unpack_integer,
    Identifier.NUMBER: _unpack_number,
    Identifier.MAPPING: _unpack_mapping,
    Identifier.ITERABLE: _unpack_iterable,
}
