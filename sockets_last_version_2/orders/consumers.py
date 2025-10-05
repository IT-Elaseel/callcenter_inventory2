import json
from channels.generic.websocket import AsyncWebsocketConsumer

# ✅ خاص بالكنترول
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
# ✅ خاص بالكول سنتر
class CallCenterConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("callcenter_updates", self.channel_name)
        await self.accept()
        print("✅ CallCenter WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("callcenter_updates", self.channel_name)
        print("⚠️ CallCenter WebSocket disconnected")

    async def callcenter_update(self, event):
        print("📡 callcenter_update event received:", event)
        await self.send(text_data=json.dumps({
            "type": "callcenter_update",
            "message": event.get("message", ""),
            "product_id": event.get("product_id"),
            "branch_id": event.get("branch_id"),
            "branch_name": event.get("branch_name"),
            "new_qty": event.get("new_qty"),
        }))
