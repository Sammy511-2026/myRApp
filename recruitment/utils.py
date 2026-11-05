from __future__ import annotations
from functools import wraps
from django.http import HttpResponseForbidden

def role_required(*roles):
    """
    Guard a view by user.role. Superusers/staff always pass.
    Usage: @role_required("APPLICANT") or @role_required("ADMIN","OFFICER")
    """
    def deco(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if u.is_superuser or u.is_staff:
                return view_func(request, *args, **kwargs)
            if hasattr(u, "role") and (u.role in roles):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped
    return deco
