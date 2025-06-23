"""Startup utilities for Skellaprompter backend."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import gui

logger = logging.getLogger(__name__)


def ensure_directories(base_path: Path) -> None:
    """Create required data directories if they do not already exist."""
    for directory in ("prompts", "vars", "prompt-vars"):
        path = base_path / directory
        path.mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured directory %s exists", path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the backend startup."""
    parser = argparse.ArgumentParser(description="Start Skellaprompter backend")
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base directory containing prompts, vars, and prompt-vars",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for starting the Skellaprompter backend."""
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    ensure_directories(args.base_path)

    logger.info("Starting Skellaprompter backend")
    gui.run(args.base_path)
    logger.info("Shutdown complete")
    return 0
