from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


class FarsiPasswordChangeForm(PasswordChangeForm):
    error_messages = {
        'password_incorrect': _("رمز عبور قدیمی اشتباه است"),
        'password_mismatch': _("رمزهای عبور جدید با هم مطابقت ندارند"),
        # Common password validation errors from Django's password validators
        'password_too_short': _("رمز عبور خیلی کوتاه است. باید حداقل 8 کاراکتر باشد"),
        'password_too_common': _("این رمز عبور خیلی رایج است"),
        'password_entirely_numeric': _("رمز عبور نمی‌تواند کاملاً عددی باشد"),
        'password_too_similar': _("رمز عبور جدید بیش از حد به اطلاعات شخصی شما شبیه است"),
    }
