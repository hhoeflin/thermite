"""A package for easily creating CLIs."""
__version__ = "0.1.0"

from .config import Config
from .run import run

__all__ = ["run", "Config"]
