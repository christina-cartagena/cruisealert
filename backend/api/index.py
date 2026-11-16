"""Vercel serverless entrypoint for the FastAPI app.

Vercel's Python runtime serves the module-level ``app`` (ASGI) variable.
``vercel.json`` rewrites every path to this function, and Vercel forwards the
original request path so FastAPI routing works unchanged.
"""
import os
import sys

# Ensure the project root (which contains the ``app`` package) is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

__all__ = ["app"]
