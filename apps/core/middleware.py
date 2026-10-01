from django.utils import translation

from .ky import translate


class LanguageMiddleware:
    """Язык берётся из cookie «lang» (ru или ky). Для ky страницы переводятся по словарю apps/core/ky.py."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get("lang", "ru")
        request.LANG = lang if lang in ("ru", "ky") else "ru"
        # если в Django есть кыргызская локаль, встроенные сообщения (формы, админка) тоже станут кыргызскими
        translation.activate("ky" if request.LANG == "ky" and translation.check_for_language("ky") else "ru")
        response = self.get_response(request)
        if (request.LANG == "ky" and not getattr(response, "streaming", False)
                and "text/html" in response.get("Content-Type", "") and response.content):
            charset = getattr(response, "charset", None) or "utf-8"
            response.content = translate(response.content.decode(charset))
            if "Content-Length" in response:
                del response["Content-Length"]
        return response
