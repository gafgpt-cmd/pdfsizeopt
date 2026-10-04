#!/usr/bin/env python3
"""Build the Python 3 executable archive with the standard library."""

from pathlib import Path
import zipapp


def main():
  root = Path(__file__).resolve().parent
  modules = {'__init__.py', 'binary.py', 'cli.py', 'cff.py', 'float_util.py',
             'image_filters.py', 'main.py', 'psproc.py'}
  for name in modules:
    source = root / 'lib' / 'pdfsizeopt' / name
    compile(source.read_text(encoding='utf-8'), str(source), 'exec')
  target = root / 'pdfsizeopt.single'
  zipapp.create_archive(
      root / 'lib', target=target, interpreter='/usr/bin/env python3',
      main='pdfsizeopt.cli:run', compressed=True,
      filter=lambda path: (path.as_posix() == 'pdfsizeopt' or
                           path.parent.as_posix() == 'pdfsizeopt' and
                           path.name in modules))
  print('Created %s (%d bytes)' % (target, target.stat().st_size))


if __name__ == '__main__':
  main()
