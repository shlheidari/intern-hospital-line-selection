"""Shared constants for the line-selection app."""

TEHRAN_TZ = 'Asia/Tehran'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Members model field -> unit name used in the Capacity / Shared tables.
# Capacity rows are named "<unit>-<line>", e.g. "جراحی-1A" (surgery, line 1A).
UNIT_FIELDS = {
    'surgery': 'جراحی',
    'internal': 'داخلی',
    'pediatrics': 'کودکان',
    'gynocology': 'زنان',
    'emergency': 'اورژانس',
    'orthopedix': 'ارتوپدی',
    'cardiology': 'قلب',
    'elective_one': 'الکتیو-اول',
    'elective_two': 'الکتیو-دوم',
    'elective_three': 'الکتیو-سوم',
}
FIELD_BY_UNIT = {unit: field for field, unit in UNIT_FIELDS.items()}

# Units every student has to choose before finishing.
REQUIRED_UNITS = [
    'ارتوپدی', 'اورژانس', 'داخلی', 'جراحی', 'قلب', 'کودکان', 'زنان',
    'الکتیو-اول', 'الکتیو-دوم', 'الکتیو-سوم',
]

SESSION_CONFLICT_MESSAGE = 'شخص دیگری وارد اکانت شما شده، مجددا وارد شوید'

# How long a password-change session stays logged in (seconds).
PASSWORD_SESSION_SECONDS = 5 * 60 * 60
