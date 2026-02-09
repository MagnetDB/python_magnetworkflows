"""Workflows for Python Magnet Workflows."""

__author__ = "Christophe Trophime"
__email__ = "christophe.trophime@lncmi.cnrs.fr"

# Version is read from package metadata (defined in pyproject.toml)
# This ensures a single source of truth for the version number
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Fallback for Python < 3.8 (though we require 3.11+)
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version("python-magnetworkflows")
except PackageNotFoundError:
    # Package not installed (e.g., running from source without install)
    # This is expected during development before running `pip install -e .`
    __version__ = "0.0.0+unknown"
