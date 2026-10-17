"""OpenTelemetry -> PRISM span instrumentation (tool calls, model calls, sessions).

The existing HTTP emitter in ``prism.py`` sends one summary trace per step. This
module adds *real spans* so PRISM can show tool calls and token usage. It is
lazy: disabled under TESTING or when credentials are absent, and it never raises
into the request path.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from flask import current_app


class Tracing:
    def __init__(self, app):
        self.app = app
        self.enabled = False
        self.exported = 0
        self.error: str | None = None
        self._tracer = None
        self._init_attempted = False

    def _ensure(self) -> None:
        if self._init_attempted:
            return
        self._init_attempted = True
        try:
            if current_app.config.get("TESTING") or self.app.config.get("TESTING"):
                return
            key = self.app.config.get("PRISMTRACE_API_KEY")
            project = self.app.config.get("PRISMTRACE_PROJECT_ID")
            host = self.app.config.get("PRISMTRACE_HOST")
            if not (key and project and host):
                return
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from prismtrace import PRISMtraceSpanExporter

            exporter = PRISMtraceSpanExporter(api_key=key, project_id=project,
                                              endpoint=host, timeout=10)
            provider = TracerProvider()
            provider.add_span_processor(BatchSpanProcessor(exporter))
            self._tracer = provider.get_tracer("moneyfinder")
            self._provider = provider
            self.enabled = True
        except Exception as exc:  # noqa: BLE001 - instrumentation must not break the app
            self.error = f"{type(exc).__name__}: {exc}"
            self.enabled = False

    def flush(self) -> None:
        """Force the batch exporter to drain. Called at request teardown."""
        provider = getattr(self, "_provider", None)
        if provider is not None:
            try:
                provider.force_flush(timeout_millis=10000)
            except Exception:  # noqa: BLE001
                pass

    def is_enabled(self) -> bool:
        self._ensure()
        try:
            if current_app.config.get("TESTING"):
                return False
        except Exception:  # noqa: BLE001
            pass
        return bool(self.enabled and self._tracer is not None)

    @contextmanager
    def span(self, name: str, session_id: str, *, span_type: str = "tool",
             tool: str | None = None, model: str | None = None,
             input_text: str | None = None, output_text: str | None = None,
             attributes: dict[str, Any] | None = None) -> Iterator[Any]:
        self._ensure()
        if not self.enabled or self._tracer is None or current_app.config.get("TESTING"):
            yield None
            return
        try:
            from opentelemetry.trace import Status, StatusCode
        except Exception:  # noqa: BLE001
            yield None
            return
        with self._tracer.start_as_current_span(name) as span:
            span.set_attribute("prismtrace.session_id", session_id)
            span.set_attribute("prismtrace.span_type", span_type)
            if tool:
                span.set_attribute("gen_ai.tool.name", tool)
                span.set_attribute("gen_ai.operation.name", "execute_tool")
            if model:
                span.set_attribute("prismtrace.model", model)
                span.set_attribute("gen_ai.request.model", model)
            if span_type == "llm":
                span.set_attribute("gen_ai.operation.name", "chat")
            if input_text:
                span.set_attribute("prismtrace.input", str(input_text)[:4000])
            if output_text:
                span.set_attribute("prismtrace.output", str(output_text)[:4000])
            for k, v in (attributes or {}).items():
                try:
                    span.set_attribute(k, v)
                except Exception:  # noqa: BLE001
                    pass
            try:
                yield span
            except Exception as exc:  # noqa: BLE001
                span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
                span.set_attribute("prismtrace.error", f"{type(exc).__name__}: {exc}"[:400])
                raise
            finally:
                self.exported += 1


def annotate(span, *, output_text: str | None = None, input_text: str | None = None,
             model: str | None = None, tokens_in: int | None = None,
             tokens_out: int | None = None, status: str | None = None,
             error: str | None = None, **attrs: Any) -> None:
    if span is None:
        return
    if error:
        span.set_attribute("prismtrace.error", str(error)[:400])
        try:
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.ERROR, str(error)[:200]))
        except Exception:  # noqa: BLE001
            pass
    if output_text:
        span.set_attribute("prismtrace.output", str(output_text)[:4000])
    if input_text:
        span.set_attribute("prismtrace.input", str(input_text)[:2000])
    if model:
        span.set_attribute("prismtrace.model", model)
    if tokens_in is not None:
        span.set_attribute("prismtrace.token_count_input", int(tokens_in))
    if tokens_out is not None:
        span.set_attribute("prismtrace.token_count_output", int(tokens_out))
    if status:
        span.set_attribute("prismtrace.status", status)
    for k, v in attrs.items():
        if v is not None:
            try:
                span.set_attribute(k, v)
            except Exception:  # noqa: BLE001
                pass


def get_tracing():
    return current_app.extensions.get("tracing")
