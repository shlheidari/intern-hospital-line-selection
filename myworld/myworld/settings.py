"""
Django settings for the line-selection project.

Configuration comes from environment variables (optionally loaded from a
``.env`` file next to this module - see ``.env.example``).
"""
import os
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# Load myworld/.env (if present) into os.environ. Variables that already exist
# in the real environment win over the file.
environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=()):
    value = os.getenv(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]


# --- Core ---------------------------------------------------------------

DEBUG = env_bool('DEBUG', False)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'The SECRET_KEY environment variable is required when DEBUG is off. '
            'See myworld/myworld/.env.example.'
        )
    SECRET_KEY = 'insecure-development-key-do-not-use-in-production'

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['localhost', '127.0.0.1', '[::1]'])
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')


# --- Applications -------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'user_sessions',
    'line.apps.LineConfig',
    'preventconcurrentlogins',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'user_sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # One active session per account.
    'line.preventconcurrentloginsfixed.FixedPreventConcurrentLoginsMiddleware',
]

if not DEBUG:
    # Serve the collected static files (CSS/JS bundles) without a separate web
    # server; in development `runserver` serves them itself.
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'myworld.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'myworld.wsgi.application'


# --- Database -----------------------------------------------------------
# Configure with DB_ENGINE / DB_NAME / DB_USER / DB_PASSWORD / DB_HOST /
# DB_PORT. The older un-prefixed names (ENGINE, NAME, USER, ...) are still
# honoured. Without any configuration a local SQLite file is used.

def db_setting(name, default=None):
    return os.getenv(f'DB_{name}') or os.getenv(name, default)


DATABASES = {
    'default': {
        'ENGINE': db_setting('ENGINE', 'django.db.backends.sqlite3'),
        'NAME': db_setting('NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': db_setting('USER'),
        'PASSWORD': db_setting('PASSWORD'),
        'HOST': db_setting('HOST'),
        'PORT': db_setting('PORT'),
    }
}


# --- Auth / sessions ----------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

SESSION_ENGINE = 'user_sessions.backends.db'


# --- Internationalisation / static files --------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # target of `manage.py collectstatic`

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# django-preventconcurrentlogins ships only an AutoField migration. Because
# DEFAULT_AUTO_FIELD is BigAutoField, the follow-up migration lives in this
# project (line/pcl_migrations) so a fresh checkout can run `migrate`.
MIGRATION_MODULES = {
    'preventconcurrentlogins': 'line.pcl_migrations',
}
