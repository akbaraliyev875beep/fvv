"""
Tez Yordam EMS — WebSocket Ulanish Menejeri (Local In-Memory)
Redis o'rniga faqat shu jarayonda ishlaydigan oddiy manager.
"""

import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger("tez_yordam.ws")

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]

    async def send_to_channel(self, channel: str, message: dict) -> None:
        if channel in self._connections:
            dead = set()
            for ws in self._connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self._connections[channel].discard(ws)

    async def broadcast_to_dispatchers(self, message: dict, service_type_code: str | None = None) -> None:
        """Barcha dispetcherlarga yoki xizmat turiga xos dispetcherlarga xabar yuborish."""
        # Umumiy dispatcher kanaliga
        await self.send_to_channel("dispatcher", message)
        # Xizmat turiga xos kanaliga ham
        if service_type_code:
            await self.send_to_channel(f"dispatcher:{service_type_code}", message)

    async def send_to_patient(self, call_id: str, message: dict) -> None:
        await self.send_to_channel(f"patient:{call_id}", message)

    async def send_to_brigade(self, brigade_id: str, message: dict) -> None:
        await self.send_to_channel(f"brigade:{brigade_id}", message)

    async def start_pubsub(self) -> None:
        pass # Local memory no need for pubsub

    async def stop_pubsub(self) -> None:
        pass

manager = ConnectionManager()
