"""Difusion en tiempo real (Server-Sent Events).

Cada commit en la base de datos publica una senal "change". Los clientes conectados a /api/events la reciben
y vuelven a pedir sus datos: asi las pantallas se actualizan al instante sin sondear. La senal no lleva datos
(por eso el endpoint puede ser publico).
"""
from __future__ import annotations

import asyncio
import logging
import threading

from sqlalchemy import event
from sqlalchemy.orm import Session

log = logging.getLogger("turi")


class Broadcaster:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def clients(self) -> int:
        return len(self._subs)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1)  # una senal pendiente basta: se agrupan las rafagas
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs.discard(q)

    def publish(self, kind: str = "change") -> None:
        """Seguro desde cualquier hilo (los endpoints sincronos corren en un pool de hilos)."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            loop.call_soon_threadsafe(_offer, q, kind)


def _offer(q: asyncio.Queue, kind: str) -> None:
    try:
        q.put_nowait(kind)
    except asyncio.QueueFull:
        pass  # ya hay una senal pendiente


broadcaster = Broadcaster()


@event.listens_for(Session, "after_commit")
def _publish_on_commit(_session) -> None:  # noqa: ANN001
    broadcaster.publish("change")
