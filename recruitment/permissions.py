from functools import wraps
from django.shortcuts import redirect
from .models import User

def role_required(roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                return redirect("recruitment:login")
            if u.role not in roles:
                return redirect("recruitment:forbidden")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

applicant_required = role_required([User.Roles.APPLICANT])
officer_required   = role_required([User.Roles.OFFICER, User.Roles.ADMIN])
admin_required     = role_required([User.Roles.ADMIN])
