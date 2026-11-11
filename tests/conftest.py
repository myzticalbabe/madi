# coding: utf-8
"""Pin this repo's `src/` at the front of sys.path.

Without this, an ambient PYTHONPATH (e.g. a sibling checkout's `src/`)
can shadow `madi` and the suite silently tests the wrong copy --
or fails on modules only this repo has. CI installs the package, where
this is a harmless no-op.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
