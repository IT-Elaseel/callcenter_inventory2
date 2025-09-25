from .forms import ArabicPasswordChangeForm

def password_change_form(request):
    if request.user.is_authenticated:
        # لو كان POST ومعاه errors → نستخدمه
        if hasattr(request, "_password_form"):
            return {"password_form": request._password_form}
        return {"password_form": ArabicPasswordChangeForm(user=request.user)}
    return {}
