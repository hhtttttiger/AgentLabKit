"""Local-first Desktop composition.

This package is deliberately separate from ``backend``.  It owns the small
SQLite-backed surface needed by the Desktop engineering loop and composes the
existing Application contracts with the existing Agent Runtime.
"""

from .composition import create_local_app

__all__ = ["create_local_app"]
