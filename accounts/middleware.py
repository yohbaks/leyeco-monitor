from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    ALLOWED_URLS = [
        '/accounts/password/',
        '/accounts/logout/',
        '/accounts/login/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, 'force_password_change', False)
            and not any(request.path.startswith(u) for u in self.ALLOWED_URLS)
        ):
            return redirect('accounts:change_password')
        return self.get_response(request)