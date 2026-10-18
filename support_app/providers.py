"""Safe, actionable provider failures: never expose raw responses or credentials."""
import requests


class ProviderError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(hint(code))


HINTS = {
    "authentication": ("OpenRouter rejected the API key. Check OPENROUTER_API_KEY (or open_router) in .env.", "رفض OpenRouter مفتاح API. تحقق من المفتاح في ملف .env."),
    "credits": ("OpenRouter rejected this request because of account credits or limits. No paid model was selected.", "رفض OpenRouter الطلب بسبب رصيد الحساب أو حدوده. لم يتم اختيار نموذج مدفوع."),
    "quota": ("OpenRouter's free quota or rate limit was reached. Wait before retrying; check your OpenRouter dashboard.", "تم بلوغ حد الطلبات المجانية في OpenRouter. انتظر قبل المحاولة وتحقق من لوحة الحساب."),
    "model": ("No compatible free model is available for this request. Retry later or set another :free model in .env.", "لا يوجد نموذج مجاني متوافق متاح لهذا الطلب. حاول لاحقاً أو اختر نموذجاً آخر ينتهي بـ :free."),
    "network": ("Cannot reach OpenRouter. Check the network/proxy used by the Python terminal.", "تعذر الوصول إلى OpenRouter. تحقق من اتصال الشبكة وإعدادات الوكيل في طرفية Python."),
    "timeout": ("The free model took too long to respond. Try again in a moment.", "استغرق النموذج المجاني وقتاً طويلاً للرد. حاول بعد قليل."),
    "format": ("The free model returned an incomplete answer or invalid source references. Try again.", "أعاد النموذج المجاني إجابة غير مكتملة أو مراجع غير صالحة. حاول مجدداً."),
    "provider": ("OpenRouter is temporarily unavailable. Try again later.", "خدمة OpenRouter غير متاحة مؤقتاً. حاول لاحقاً."),
}


def hint(code, language="en"):
    return HINTS.get(code, HINTS["provider"])[language == "ar"]


def failure_code(exc):
    if isinstance(exc, ProviderError):
        return exc.code
    if isinstance(exc, requests.Timeout):
        return "timeout"
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return {401: "authentication", 403: "authentication", 402: "credits", 429: "quota",
                400: "model", 404: "model", 422: "model"}.get(status, "provider")
    if isinstance(exc, requests.RequestException):
        return "network"
    return "format"
