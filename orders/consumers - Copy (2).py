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
            "action": event.get("action"),                # ✅ أضفها
            "message": event.get("message", ""),
            "product_id": event.get("product_id"),
            "product_name": event.get("product_name"),    # ✅ أضفها
            "category_name": event.get("category_name"),  # ✅ أضفها
            "branch_id": event.get("branch_id"),
            "branch_name": event.get("branch_name"),
            "new_qty": event.get("new_qty"),
            "unit": event.get("unit"),                    # ✅ أضفها برضو لو موجودة
        }))

# ✅ خاص بصفحة الفروع
class BranchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("branch_updates", self.channel_name)
        await self.accept()
        print("🏬 Branch WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("branch_updates", self.channel_name)
        print("⚠️ Branch WebSocket disconnected")

    async def branch_update(self, event):
        print("📩 branch_update event received:", event)
        await self.send(text_data=json.dumps({
            "type": "branch_update",
            "message": event.get("message", ""),
            "reservation_id": event.get("reservation_id"),
            "customer_name": event.get("customer_name"),
            "customer_phone": event.get("customer_phone"),
            "product_name": event.get("product_name"),
            "quantity": event.get("quantity"),
            "created_at": event.get("created_at"),
            "reserved_by": event.get("reserved_by"),
        }))
# consumers.py
# class ReservationsConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         await self.channel_layer.group_add("reservations_updates", self.channel_name)
#         await self.accept()
#         print("📋 Reservations WebSocket connected")
#
#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard("reservations_updates", self.channel_name)
#         print("⚠️ Reservations WebSocket disconnected")
#
#     # ✅ اسم الهاندلر لازم يطابق "type" اللي هنبعته من الجروب
#     async def reservations_update(self, event):
#         await self.send(text_data=json.dumps({
#             "action": event.get("action", "new"),  # new | status_change
#             "message": event.get("message", ""),
#             "reservation_id": event.get("reservation_id"),
#             "customer_name": event.get("customer_name"),
#             "customer_phone": event.get("customer_phone"),
#             "product_name": event.get("product_name"),
#             "quantity": event.get("quantity"),
#             "branch_name": event.get("branch_name"),
#             "delivery_type": event.get("delivery_type"),
#             "status": event.get("status"),
#             "created_at": event.get("created_at"),
#             "decision_at": event.get("decision_at"),
#             "reserved_by": event.get("reserved_by"),
#         }))
class ReservationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("reservations_updates", self.channel_name)
        await self.accept()
        print("📋 Reservations WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("reservations_updates", self.channel_name)
        print("⚠️ Reservations WebSocket disconnected")

    # 👇 لازم يكون نفس الاسم الموجود في type بالـ group_send
    async def reservations_update(self, event):
        print("📢 reservations_update event received:", event)
        await self.send(text_data=json.dumps({
            "action": event.get("action", ""),
            "message": event.get("message", ""),
            "reservation_id": event.get("reservation_id"),
            "customer_name": event.get("customer_name"),
            "customer_phone": event.get("customer_phone"),
            "product_name": event.get("product_name"),
            "quantity": event.get("quantity"),
            "branch_name": event.get("branch_name"),
            "delivery_type": event.get("delivery_type"),
            "status": event.get("status"),
            "created_at": event.get("created_at"),
            "decision_at": event.get("decision_at"),
            "branch_last_modified_at": event.get("branch_last_modified_at"),
            "reserved_by": event.get("reserved_by"),
        }))
