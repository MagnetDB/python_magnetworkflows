"""Pytest configuration and shared fixtures.

Mocks unavailable system-level packages (feelpp Debian packages and
python_magnetcooling when the submodule is not installed) so that the
test suite can run in a plain CI environment without Feel++.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock feelpp – installed only as Debian system packages
# ---------------------------------------------------------------------------
_FEELPP_MODS = [
    "feelpp",
    "feelpp.core",
    "feelpp.toolboxes",
    "feelpp.toolboxes.core",
    "feelpp.toolboxes.cfpdes",
]
for _mod in _FEELPP_MODS:
    sys.modules.setdefault(_mod, MagicMock())

# ---------------------------------------------------------------------------
# Mock python_magnetcooling when the submodule has not been installed
# ---------------------------------------------------------------------------
try:
    import python_magnetcooling  # noqa: F401
except ImportError:
    _COOLING_MODS = [
        "python_magnetcooling",
        "python_magnetcooling.cooling",
        "python_magnetcooling.feelpp",
        "python_magnetcooling.thermohydraulics",
    ]
    for _mod in _COOLING_MODS:
        sys.modules.setdefault(_mod, MagicMock())
