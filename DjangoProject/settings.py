"""
Django settings for DjangoProject project.
Simplified - Public YouTube Browser (No Authentication)
"""

import os
import socket
from pathlib import Path
from decouple import config, Csv

# ============================================
# BASE
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Auto-sync secret token
AUTO_SYNC_SECRET_TOKEN = config('AUTO_SYNC_TOKEN')

# ============================================
# INSTALLED APPS - REMOVED ALL social_django references
# ============================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sonyApp',                    # Your app
    'background_task',             # Keep if you're using it
]

# ============================================
# AUTHENTICATION - REMOVED Google OAuth completely
# ============================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Only Django's default auth
]

# ============================================
# MIDDLEWARE - REMOVED all social_django and custom middleware
# ============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # REMOVED: 'social_django.middleware.SocialAuthExceptionMiddleware',
    # REMOVED: 'sonyApp.middleware.SonySubscriptionMiddleware',
]

ROOT_URLCONF = 'DjangoProject.urls'

# ============================================
# TEMPLATES - REMOVED social_django context processors
# ============================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # REMOVED: 'social_django.context_processors.backends',
                # REMOVED: 'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'DjangoProject.wsgi.application'

# ============================================
# DATABASE
# ============================================

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE':       'django.db.backends.postgresql',
            'NAME':         config('DB_NAME'),
            'USER':         config('DB_USER'),
            'PASSWORD':     config('DB_PASSWORD'),
            'HOST':         config('DB_HOST'),
            'PORT':         config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 0,
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

# ============================================
# PASSWORD VALIDATION
# ============================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================
# INTERNATIONALISATION
# ============================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ============================================
# STATIC & MEDIA FILES
# ============================================

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

# ============================================
# YOUTUBE API - Network Fixes (KEEP THIS)
# ============================================

YOUTUBE_API_KEY = config('YOUTUBE_API_KEY')
MAX_VIDEOS_PER_CHANNEL = 50
VIDEOS_PER_PAGE = 20

# Fix for IPv6 timeout issues
socket.setdefaulttimeout(60)

# Force IPv4
try:
    import urllib3.util.connection
    urllib3.util.connection.HAS_IPV6 = False
except ImportError:
    pass

# Force IPv4 at httplib2 level
try:
    import httplib2
    original_getaddrinfo = socket.getaddrinfo
    def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    socket.getaddrinfo = getaddrinfo_ipv4_only
except ImportError:
    pass

# ============================================
# SESSION (minimal)
# ============================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# ============================================
# SECURITY (production only)
# ============================================

if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# ============================================
# CACHING
# ============================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sonyapp-cache',
        'TIMEOUT': 3600,
    }
}

# ============================================
# LOGGING
# ============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'sonyApp': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# ============================================
# MISC
# ============================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MAX_ATTEMPTS = 3
MAX_RUN_TIME = 3600
INTERNAL_IPS = ['127.0.0.1']