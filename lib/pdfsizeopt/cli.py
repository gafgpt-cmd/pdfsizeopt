"""Entry point for the standalone Python archive."""

import sys

from pdfsizeopt import main


def run():
  sys.exit(main.main(sys.argv, zip_file=sys.argv[0]))
