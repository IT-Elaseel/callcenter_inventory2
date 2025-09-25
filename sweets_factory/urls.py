"""
URL configuration for sweets_factory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from orders.views import root_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", root_redirect, name="root_redirect"),  # 👈 الصفحة الرئيسية تبقى Redirect
    path("", include("orders.urls")),  # ده هيخلي home page تروح للـ app بتاعنا

]
