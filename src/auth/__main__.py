"""Main entry point for the auth service."""

import argparse
import logging
import logging.config
from pathlib import Path

import uvicorn
import yaml


def _read_config_file(path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Auth service CLI")
    parser.add_argument("--host", help="Address to listen on to run on")
    parser.add_argument("--port", type=int, help="Port to run on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    logging.config.dictConfig(
        _read_config_file(Path("/code/logging.yml")),
    )

    uvicorn.run("auth.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
