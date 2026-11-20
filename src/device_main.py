"""Start the precompiled CYD application on MicroPython."""

import sys

sys.path.insert(0, '/cyd')
from bitcoin_main import main

main()
