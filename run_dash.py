#!/usr/bin/env python3
"""
Entry point for The Convenience Paradox dashboard.

Usage:
    python run_dash.py [--debug] [--port PORT]

The dashboard runs at http://localhost:8050 by default.
"""

import argparse
import logging

from dash_app.app import create_app


def main():
    parser = argparse.ArgumentParser(description="Run The Convenience Paradox dashboard")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with hot-reloading")
    parser.add_argument("--port", type=int, default=8050, help="Port to serve on (default: 8050)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = create_app(debug=args.debug)

    logging.getLogger(__name__).info(
        "Starting dashboard at http://%s:%d", args.host, args.port
    )

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
