"""Channels: how a request travels to a decider and back without blocking the loop.

The architecture calls `submit()` and later, once per tick, `poll()`. Both return
immediately. Two implementations with the same methods:

SimChannel   for the simulated clock. The answer is computed at once, but it is
             only *delivered* when virtual time reaches send time + latency.
             Deterministic: the same seed gives the same arrivals.

ThreadChannel for the real clock. A small pool of background worker threads
             runs the requests; finished answers are put on a thread-safe queue
             that the loop drains on each tick. This is real concurrency: the
             game keeps ticking while the network request is in flight.
"""

from __future__ import annotations

import heapq
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from .deciders import Answer, TIMEOUT_MS


@dataclass(order=True)
class Arrival:
    arrived_at: float
    req_id: int
    answer: Answer = field(compare=False)
    sent_at: float = field(compare=False)
    tag: Any = field(compare=False, default=None)  # whatever the architecture attached

    @property
    def elapsed_ms(self) -> float:
        return (self.arrived_at - self.sent_at) * 1000


class SimChannel:
    def __init__(self, decider):
        self.decider = decider
        self._heap: list[Arrival] = []

    def submit(self, req_id: int, state, now: float, tag=None) -> None:
        ans = self.decider.decide(state)
        if not ans.ok:
            # A failed request is noticed when the HTTP timeout fires.
            ans.latency_ms = ans.latency_ms if ans.latency_ms > 0 else TIMEOUT_MS
        heapq.heappush(self._heap, Arrival(now + ans.latency_ms / 1000, req_id, ans, now, tag))

    def poll(self, now: float) -> list[Arrival]:
        out = []
        while self._heap and self._heap[0].arrived_at <= now + 1e-12:
            out.append(heapq.heappop(self._heap))
        return out

    @property
    def in_flight(self) -> int:
        return len(self._heap)

    def close(self) -> None:
        pass


class ThreadChannel:
    """`make_decider` is called once per worker thread: an HTTP connection must
    not be shared between threads, so each worker gets its own client."""

    def __init__(self, make_decider: Callable[[], Any], clock, workers: int = 4):
        self.clock = clock
        self._local = threading.local()
        self._make = make_decider
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="jev")
        self._done: queue.Queue[Arrival] = queue.Queue()
        self._deciders: list = []
        self._lock = threading.Lock()
        self._inflight = 0

    def _decider(self):
        d = getattr(self._local, "decider", None)
        if d is None:
            d = self._local.decider = self._make()
            with self._lock:
                self._deciders.append(d)
        return d

    def _run(self, req_id: int, state, sent_at: float, tag) -> None:
        d = self._decider()
        ans = d.decide(state)
        if not getattr(d, "real_time", False):
            time.sleep(ans.latency_ms / 1000)  # a simulated Jev on the real clock
        self._done.put(Arrival(self.clock.now(), req_id, ans, sent_at, tag))
        with self._lock:
            self._inflight -= 1

    def submit(self, req_id: int, state, now: float, tag=None) -> None:
        with self._lock:
            self._inflight += 1
        self._pool.submit(self._run, req_id, state, now, tag)

    def poll(self, now: float) -> list[Arrival]:
        out = []
        while True:
            try:
                out.append(self._done.get_nowait())
            except queue.Empty:
                return sorted(out)

    @property
    def in_flight(self) -> int:
        return self._inflight

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        for d in self._deciders:
            if hasattr(d, "close"):
                d.close()


