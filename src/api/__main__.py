"""Entry point CLI: uvicorn src.api.app:create_app --factory.

Uso:
    python -m src.api [--host HOST] [--port PORT] [--reload]
"""

from __future__ import annotations

import argparse


def main() -> None:
    """Arranca el servidor uvicorn con create_app factory."""
    parser = argparse.ArgumentParser(description="PhishGuard-AI API REST")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Hot reload (dev)")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "src.api.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
