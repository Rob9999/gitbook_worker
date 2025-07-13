#!/usr/bin/env python3
"""Convenience wrapper to run gitbook-worker via Docker."""
from __future__ import annotations

import sys
from gitbook_worker.docker_cli import main as docker_main


def main(args: list[str] | None = None) -> None:
    docker_main(args)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
