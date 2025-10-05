from django.contrib import admin
from django.urls import path, include
from orders.views import root_redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", root_redirect, name="root_redirect"),  # 👈 الصفحة الرئيسية تبقى Redirect
    path("", include("orders.urls")),  # ده هيخلي home page تروح للـ app بتاعنا
    path("hr/", include("hr.urls")),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
