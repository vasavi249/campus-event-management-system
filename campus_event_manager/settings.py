import os
import sys
from pathlib import Path

# Python 3.14 Django template context compatibility patch
if sys.version_info >= (3, 14):
    try:
        import copy as _copy_module
        from django.template.context import BaseContext, Context, RequestContext, RenderContext

        def _base_context_copy(self):
            duplicate = object.__new__(self.__class__)
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = [d.copy() for d in self.dicts]
            if hasattr(self, 'render_context'):
                duplicate.render_context = _copy_module.copy(self.render_context)
            return duplicate

        def _render_context_copy(self):
            duplicate = object.__new__(RenderContext)
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = [d.copy() for d in self.dicts]
            return duplicate

        BaseContext.__copy__ = _base_context_copy
        Context.__copy__ = _base_context_copy
        RequestContext.__copy__ = _base_context_copy
        RenderContext.__copy__ = _render_context_copy
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-campus-event-management-system-secret-key'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',

    # Local apps
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'campus_event_manager.urls'

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

WSGI_APPLICATION = 'campus_event_manager.wsgi.application'

try:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
            conn_max_age=600,
        )
    }
except ImportError:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }



AUTH_USER_MODEL = 'events.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Cloud deployment & Proxy HTTPS Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 1209600  # 14 days
SESSION_COOKIE_HTTPONLY = True

# Automatically enable secure cookies in production/Render environment
if not DEBUG or os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'



