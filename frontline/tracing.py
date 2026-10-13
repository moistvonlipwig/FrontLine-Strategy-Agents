# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""OpenTelemetry setup: spans are kept in memory during a game, then saved as one JSON file.

Span tree per game:
    game
    └── turn (x24)
        ├── retrieve
        ├── decide      (+ one event per tool call)
        ├── validate
        └── apply
"""

import json
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))  # Simple = export each span as it ends
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("frontline")


def save_spans(path: str | Path) -> Path:
    """Write every finished span to `path` as a JSON list, then clear for the next game."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    spans = [json.loads(s.to_json()) for s in _exporter.get_finished_spans()]
    path.write_text(json.dumps(spans, indent=1))
    _exporter.clear()
    return path
