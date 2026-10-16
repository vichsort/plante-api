"""Apoio comum às tasks do Celery."""
from src.shared.workers.async_runner import run_async

__all__ = ["run_async"]
