"""The retriever library."""
# We disable a Flake8 check for "Module imported but unused (F401)" here because
# although this import is not directly used, it populates the value
# package_name.__version__, which is used to get version information about this
# Python package.
from . import retriever
from ._version import __version__  # noqa: F401
from .get_partswiki_imgs import main as partswiki_main
from .get_snapon_catalogs import main as snapon_main

__all__ = ["retriever", "partswiki_main", "snapon_main"]
