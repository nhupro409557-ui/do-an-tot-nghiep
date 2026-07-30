import threading
import time


FAILURE_WINDOW_SECONDS = 60
OPEN_SECONDS = 120
FAILURE_THRESHOLD = 3

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}
_open_until: dict[str, float] = {}


def is_local_circuit_open(model: str, *, now: float | None = None) -> bool:
    current = time.monotonic() if now is None else now
    with _lock:
        open_until = _open_until.get(model, 0)
        if open_until <= current:
            _open_until.pop(model, None)
            return False
        return True


def record_local_failure(
    model: str,
    *,
    now: float | None = None,
    open_immediately: bool = False,
    open_seconds: int = OPEN_SECONDS,
) -> None:
    current = time.monotonic() if now is None else now
    with _lock:
        if open_immediately:
            _open_until[model] = current + open_seconds
            _failures.pop(model, None)
            return
        recent = [
            timestamp
            for timestamp in _failures.get(model, [])
            if current - timestamp <= FAILURE_WINDOW_SECONDS
        ]
        recent.append(current)
        if len(recent) >= FAILURE_THRESHOLD:
            _open_until[model] = current + open_seconds
            _failures.pop(model, None)
        else:
            _failures[model] = recent


def clear_local_model_state(model: str) -> None:
    with _lock:
        _failures.pop(model, None)
        _open_until.pop(model, None)


def get_local_circuit_status(model: str, *, now: float | None = None) -> dict:
    current = time.monotonic() if now is None else now
    with _lock:
        open_until = _open_until.get(model, 0)
        if open_until <= current:
            _open_until.pop(model, None)
            open_until = 0
        recent = [
            timestamp
            for timestamp in _failures.get(model, [])
            if current - timestamp <= FAILURE_WINDOW_SECONDS
        ]
        if recent:
            _failures[model] = recent
        else:
            _failures.pop(model, None)
        return {
            "model": model,
            "open": open_until > current,
            "ttl_seconds": max(int(open_until - current), 0),
            "recent_failures": len(recent),
            "status": "LOCAL_FALLBACK",
        }
