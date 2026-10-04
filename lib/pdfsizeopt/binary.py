"""Explicit byte boundaries for PDF/PostScript octet strings.

The parser represents each byte as the same-valued Latin-1 character. This is
not PDF text decoding: all 256 values round-trip, and offsets remain byte
offsets. Paths and human-readable messages are ordinary Unicode strings.
"""

import builtins
import struct
import subprocess
import zlib


def octets(data):
  return data.encode('latin-1') if isinstance(data, str) else bytes(data)


def string(data):
  return data.decode('latin-1')


class buffer(str):
  def __new__(cls, data, offset=0, size=None):
    if not isinstance(data, str):
      data = string(data)
    return super().__new__(cls, data[offset:] if size is None
                           else data[offset:offset + size])


def open_octets(path, mode):
  return OctetFile(builtins.open(path, mode))


class OctetFile:
  def __init__(self, file):
    self.file = file
    self.name = file.name

  def read(self, *args):
    return string(self.file.read(*args))

  def write(self, data):
    return self.file.write(octets(data))

  def seek(self, *args):
    return self.file.seek(*args)

  def tell(self):
    return self.file.tell()

  def close(self):
    self.file.close()

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()


def pack(fmt, *values):
  return string(struct.pack(fmt, *values))


def unpack(fmt, data):
  return tuple(string(value) if isinstance(value, bytes) else value
               for value in struct.unpack(fmt, octets(data)))


def compress(data, level=-1):
  return string(zlib.compress(octets(data), level))


def decompress(data, *args):
  return string(zlib.decompress(octets(data), *args))


def adler32(data):
  return zlib.adler32(octets(data))


def crc32(data):
  return zlib.crc32(octets(data))


class decompressobj:
  def __init__(self, *args):
    self.decoder = zlib.decompressobj(*args)

  def decompress(self, data):
    return string(self.decoder.decompress(octets(data)))

  def flush(self):
    return string(self.decoder.flush())

  @property
  def unused_data(self):
    return string(self.decoder.unused_data)


class compressobj:
  def __init__(self, *args):
    self.encoder = zlib.compressobj(*args)

  def compress(self, data):
    return string(self.encoder.compress(octets(data)))

  def flush(self, *args):
    return string(self.encoder.flush(*args))


class CommandOutput:
  """Binary command output with the status convention used by os.popen."""
  def __init__(self, command):
    # The caller builds a quoted command with intentional shell redirection.
    # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
    self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)

  def read(self, *args):
    return string(self.process.stdout.read(*args))

  def readline(self, *args):
    return string(self.process.stdout.readline(*args))

  def __iter__(self):
    for line in self.process.stdout:
      yield string(line)

  def close(self):
    self.process.stdout.close()
    status = self.process.wait()
    return status << 8 if status else None
