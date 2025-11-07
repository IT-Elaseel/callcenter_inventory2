import json
from channels.generic.websocket import AsyncWebsocketConsumer
from decimal import Decimal
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
        # print("📡 callcenter_update event received:", event)
        # 🟢 شكل منسق وواضح في اللوج
        try:
            product_name = event.get("product_name", "-")
            branch_name = event.get("branch_name", "-")
            qty = event.get("new_qty", "-")
            unit = event.get("unit", "")
            print(f"[WS] Updated: {product_name} | فرع {branch_name} → {qty} {unit}")
        except Exception as e:
            print("⚠️ Error formatting log:", e)


        # 🧩 تأمين القيم قبل التحويل لـ JSON
        safe_event = {}
        for k, v in event.items():
            if isinstance(v, Decimal):
                safe_event[k] = str(v)  # نحول Decimal لنص
            else:
                safe_event[k] = v

        await self.send(text_data=json.dumps({
            "type": "callcenter_update",
            "action": safe_event.get("action"),
            "message": safe_event.get("message", ""),
            "product_id": safe_event.get("product_id"),
            "product_name": safe_event.get("product_name"),
            "category_name": safe_event.get("category_name"),
            "branch_id": safe_event.get("branch_id"),
            "branch_name": safe_event.get("branch_name"),
            "new_qty": safe_event.get("new_qty"),  # 👈 الآن مؤمن
            "unit": safe_event.get("unit"),
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
class ReservationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("reservations_updates", self.channel_name)
        await self.accept()
        print("📋 Reservations WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("reservations_updates", self.channel_name)
        print("⚠️ Reservations WebSocket disconnected")

    async def reservations_update(self, event):
        try:
            # 🧩 تأمين القيم قبل تحويلها إلى JSON
            safe_event = {}
            for k, v in event.items():
                if isinstance(v, Decimal):
                    safe_event[k] = float(v)
                else:
                    safe_event[k] = v

            # 🎨 طباعة منسقة وواضحة في اللوج
            product = safe_event.get("product_name", "-")
            branch = safe_event.get("branch_name", "-")
            qty = safe_event.get("quantity", "-")
            customer = safe_event.get("customer_name", "-")
            delivery = safe_event.get("delivery_type", "")
            status = safe_event.get("status", "")
            print(f"[WS] 🆕 حجز جديد: {product} × {qty} | {branch} | {delivery} | {customer} ({status})")

            # 📨 إرسال البيانات إلى الواجهة
            await self.send(text_data=json.dumps({
                "action": safe_event.get("action", ""),
                "message": safe_event.get("message", ""),
                "reservation_id": safe_event.get("reservation_id"),
                "customer_name": customer,
                "customer_phone": safe_event.get("customer_phone"),
                "product_name": product,
                "quantity": qty,
                "branch_name": branch,
                "delivery_type": delivery,
                "status": status,
                "created_at": safe_event.get("created_at"),
                "decision_at": safe_event.get("decision_at"),
                "branch_last_modified_at": safe_event.get("branch_last_modified_at"),
                "reserved_by": safe_event.get("reserved_by"),
                "last_modified_by": safe_event.get("last_modified_by", "-"),  # ✅ الجديد

            }))

        except Exception as e:
            print("⚠️ Error in reservations_update:", e)
