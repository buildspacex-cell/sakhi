"""Application entrypoints for Sakhi."""

from importlib import import_module

worker = import_module("sakhi.apps.worker")

__all__ = ["worker"]
