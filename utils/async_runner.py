from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(object)


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
    if on_success:
        worker.signals.succeeded.connect(on_success)
    if on_error:
        worker.signals.failed.connect(on_error)
    thread_pool.start(worker)
    return worker
