from django.http import HttpResponseForbidden
from django.shortcuts import render

def role_required(allowed_roles=[]):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "orders/no_permission.html", {
                    "message": "🚫 لازم تسجل دخول"
                }, status=403)

            profile = getattr(request.user, "userprofile", None)

            # ✅ Admin (superuser/staff أو role=admin) يقدر يخش أي صفحة
            if request.user.is_superuser or request.user.is_staff:
                return view_func(request, *args, **kwargs)
            if profile and profile.role == "admin":
                return view_func(request, *args, **kwargs)

            # ✅ لو دوره ضمن المسموح
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # 🚫 لو مش مسموح
            return render(request, "orders/no_permission.html", {
                "message": "🚫 غير مسموح لك بدخول هذه الصفحة"
            }, status=403)
        return _wrapped_view
    return decorator
