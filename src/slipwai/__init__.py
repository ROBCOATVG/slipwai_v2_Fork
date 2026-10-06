"""Slipwai's keel: the core that every package attaches to.

The keel holds the questions the interview asks, the code that writes a project, the toolkit, the adoption
path and the delivery loop. It names no language and no extension of its own: those are packages, found
through the chandlery, installed into `~/.slipwai/packages/`, and answered through the registry. `cli` is
the entry point.

Nothing here reads the working directory. Every path is resolved from this package's own location, so the
same answers produce the same project from wherever the command is run.
"""
