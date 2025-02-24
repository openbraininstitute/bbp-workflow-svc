"""Main entry point for the app service."""

import argparse

from app.main import main as app


def main():
    """Main entry point for the app service."""
    parser = argparse.ArgumentParser(description="App service CLI")
    parser.add_argument("--host", help="Address to listen on to run on")
    parser.add_argument("--port", type=int, help="Port to run on")

    args = parser.parse_args()
    app(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
