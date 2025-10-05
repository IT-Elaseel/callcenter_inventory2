# hr/utils.py
def is_hr(user):
    """يتأكد إن المستخدم ليه دور HR"""
    return hasattr(user, "userprofile") and user.userprofile.role == "hr"

def is_hr_help(user):
    """يتأكد إن المستخدم ليه دور HR Help"""
    return hasattr(user, "userprofile") and user.userprofile.role == "hr_help"
def is_hr_or_hr_help(user):
    return user.is_authenticated and (
        getattr(user.userprofile, "role", None) in ["hr", "hr_help"]
    )
def is_admin_or_hr_or_hr_help(user):
    return user.is_authenticated and (
        getattr(user.userprofile, "role", None) in ["hr", "hr_help","admin"]
    )
def is_admin_or_hr(user):
    return user.is_authenticated and (
        getattr(user.userprofile, "role", None) in ["hr","admin"]
    )
def is_admin(user):
    return user.is_authenticated and (
        getattr(user.userprofile, "role", None) in ["admin"]
    )
