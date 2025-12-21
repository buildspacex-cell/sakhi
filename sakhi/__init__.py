"""Root package exports."""

from importlib import import_module

apps = import_module("sakhi.apps")

__all__ = ["apps"]
