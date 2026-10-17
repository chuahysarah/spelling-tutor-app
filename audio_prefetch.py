"""Thread-safe background prefetch for short speech clips."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import RLock
from typing import Callable


class AudioPrefetcher:
    """Schedule unique (text, language) audio tasks and reuse their futures."""

    def __init__(
        self,
        generator: Callable[[str, str], bytes],
        max_workers: int = 2,
        max_entries: int = 64,
    ) -> None:
        self._generator = generator
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="speech-prefetch",
        )
        self._max_entries = max_entries
        self._futures: dict[tuple[str, str], Future[bytes]] = {}
        self._lock = RLock()

    @staticmethod
    def _failed(future: Future[bytes]) -> bool:
        if future.cancelled():
            return True
        if not future.done():
            return False
        try:
            return future.exception() is not None
        except BaseException:
            return True

    def prefetch(self, text: str, language: str) -> Future[bytes]:
        key = (text, language)
        with self._lock:
            future = self._futures.get(key)
            if future is None or self._failed(future):
                future = self._executor.submit(self._generator, text, language)
                self._futures[key] = future
            self._prune(keep=key)
            return future

    def _prune(self, keep: tuple[str, str]) -> None:
        if len(self._futures) <= self._max_entries:
            return
        for key, future in list(self._futures.items()):
            if key != keep and future.done():
                del self._futures[key]
                if len(self._futures) <= self._max_entries:
                    break
