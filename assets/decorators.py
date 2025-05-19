from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, '🚫 Access Denied: You do not have permission to perform this action.')
        return redirect('asset_list')
    return _wrapped_view 