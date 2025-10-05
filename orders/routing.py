from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 🔹 السوكيت القديم بتاع الكنترول (سيبه زي ما هو)
    re_path(r"^ws/control/$", consumers.ControlRequestsConsumer.as_asgi()),
     # 🔹 السوكيت الجديد للكول سنتر
    re_path(r"^ws/callcenter/$", consumers.CallCenterConsumer.as_asgi()),

    re_path(r"^ws/branch/$", consumers.BranchConsumer.as_asgi()),

    re_path(r"^ws/reservations/$", consumers.ReservationsConsumer.as_asgi()),  # ✅ جديد


]
