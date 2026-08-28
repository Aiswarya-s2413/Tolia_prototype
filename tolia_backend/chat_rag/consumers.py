import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from channels.generic.websocket import AsyncWebsocketConsumer
from .rag_engine import LocalRAGEngine
from .models import Department

executor = ThreadPoolExecutor(max_workers=10)

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_query_task = None
        self.is_cancelled = False

    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "⚡ Full-Duplex WebSocket Connected to Tolia AI Brain."
        }))

    async def disconnect(self, close_code):
        self.is_cancelled = True
        if self.active_query_task and not self.active_query_task.done():
            self.active_query_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON format."
            }))
            return

        action = payload.get("action") or payload.get("type", "query")

        # 1. Instant Barge-In Cancellation Frame
        if action == "cancel":
            self.is_cancelled = True
            if self.active_query_task and not self.active_query_task.done():
                self.active_query_task.cancel()
            await self.send(text_data=json.dumps({
                "type": "cancelled",
                "message": "Stream generation halted by user barge-in."
            }))
            return

        # 2. Query Processing Frame
        if action == "query" or "query" in payload:
            if self.active_query_task and not self.active_query_task.done():
                self.active_query_task.cancel()

            self.is_cancelled = False
            user_query = payload.get("query", "").strip()
            user_role = payload.get("user_role", Department.QC)
            language = payload.get("language")

            if not user_query:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Query cannot be empty."
                }))
                return

            self.active_query_task = asyncio.create_task(
                self.stream_rag_response(user_query, user_role, language)
            )

    async def stream_rag_response(self, user_query, user_role, language):
        """
        Runs LocalRAGEngine.query_stream in a background thread and yields tokens/sentences to WebSocket in real-time.
        """
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def producer():
            from django.db import close_old_connections
            close_old_connections()
            try:
                for raw_sse in LocalRAGEngine.query_stream(user_query, user_role=user_role, target_lang=language):
                    if self.is_cancelled:
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, raw_sse)
            except Exception as ex:
                loop.call_soon_threadsafe(queue.put_nowait, ex)
            finally:
                close_old_connections()
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(executor, producer)

        try:
            while not self.is_cancelled:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": f"Streaming error: {str(item)}"
                    }))
                    break

                clean_line = item.strip()
                if clean_line.startswith("data: "):
                    json_str = clean_line[6:]
                    try:
                        event_data = json.loads(json_str)
                        await self.send(text_data=json.dumps(event_data))
                    except Exception:
                        await self.send(text_data=json_str)

        except asyncio.CancelledError:
            pass
