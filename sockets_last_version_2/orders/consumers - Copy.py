import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ControlRequestsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("control_updates", self.channel_name)
        await self.accept()
        print("✅ WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("control_updates", self.channel_name)

    async def control_update(self, event):
        await self.send(text_data=json.dumps({
            "action": event["action"],
            "message": event.get("message", ""),
            "order_number": event.get("order_number")
        }))
