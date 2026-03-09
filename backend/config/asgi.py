"""
ASGI config for SalesPipeline project.
Supports HTTP and WebSocket protocols via Django Channels.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django_asgi_app = get_asgi_application()

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PipelineConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time pipeline updates."""

    async def connect(self):
        self.pipeline_id = self.scope["url_route"]["kwargs"].get("pipeline_id", "default")
        self.room_group_name = f"pipeline_{self.pipeline_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        event_type = content.get("type", "pipeline.update")
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "pipeline_update",
                "data": content.get("data", {}),
                "event": event_type,
            },
        )

    async def pipeline_update(self, event):
        await self.send_json(
            {
                "type": event.get("event", "pipeline.update"),
                "data": event.get("data", {}),
            }
        )


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time user notifications."""

    async def connect(self):
        if self.scope.get("user") and not self.scope["user"].is_anonymous:
            self.user_group = f"notifications_{self.scope['user'].id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.accept()
        else:
            await self.accept()
            self.user_group = "notifications_anonymous"
            await self.channel_layer.group_add(self.user_group, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def send_notification(self, event):
        await self.send_json(
            {
                "type": "notification",
                "data": event.get("data", {}),
            }
        )


websocket_urlpatterns = [
    path("ws/pipeline/<str:pipeline_id>/", PipelineConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
