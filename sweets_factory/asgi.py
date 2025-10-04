import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import orders.routing
import hr.routing  # ✅ أضف ده

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sweets_factory.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            orders.routing.websocket_urlpatterns +
            hr.routing.websocket_urlpatterns  # ✅ ضيفها هنا
        )
    ),
})
