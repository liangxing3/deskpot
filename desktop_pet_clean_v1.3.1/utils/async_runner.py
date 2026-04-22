from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QCoreApplication, QObject, QRunnable, QThreadPool, Qt, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(object)


class CallbackRelay(QObject):
    """Marshals worker results back onto the GUI thread."""

    def __init__(
        self,
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or QCoreApplication.instance())
        self._on_success = on_success
        self._on_error = on_error

    @Slot(object)
    def handle_success(self, result: Any) -> None:
        if self._on_success is not None:
            self._on_success(result)

    @Slot(object)
    def handle_failure(self, exc: Exception) -> None:
        if self._on_error is not None:
            self._on_error(exc)


class FunctionWorker(QRunnable):
    def __init__(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.func(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover - requires threaded failure.
            self.signals.failed.emit(exc)
        else:
            self.signals.succeeded.emit(result)


def submit_task(
    thread_pool: QThreadPool,
    func: Callable,
    *,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> FunctionWorker:
    worker = FunctionWorker(func, *(args or ()), **(kwargs or {}))
    if on_success or on_error:
        relay = CallbackRelay(on_success=on_success, on_error=on_error)
        worker._callback_relay = relay
        if on_success:
            worker.signals.succeeded.connect(relay.handle_success, Qt.QueuedConnection)
        if on_error:
            worker.signals.failed.connect(relay.handle_failure, Qt.QueuedConnection)
    thread_pool.start(worker)
    return worker
