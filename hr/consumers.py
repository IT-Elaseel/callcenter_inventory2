import json
from channels.generic.websocket import AsyncWebsocketConsumer

# ✅ Consumer خاص بطلبات الـ HR (المتقدمين)
class HRApplicantsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("hr_applicants", self.channel_name)
        await self.accept()
        print("✅ HR Applicants WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("hr_applicants", self.channel_name)

    async def hr_applicant_update(self, event):
        # إرسال كل البيانات إلى الصفحة
        await self.send(text_data=json.dumps(event))
