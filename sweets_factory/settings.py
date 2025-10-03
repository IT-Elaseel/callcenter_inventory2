import os
from pathlib import Path
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# تهيئة env
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# 🔹 مفاتيح أساسية
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://inv.el-aseel.com"]
)

# 🔹 التطبيقات
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",

    # Static files
    "whitenoise.runserver_nostatic",  # ✅ إضافة WhiteNoise للـ dev
    "django.contrib.staticfiles",

    # تطبيقاتك
    "orders",
    "hr",
]

# 🔹 Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ إضافة WhiteNoise
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sweets_factory.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "orders.context_processors.password_change_form",
            ],
        },
    },
]

WSGI_APPLICATION = "sweets_factory.wsgi.application"

# 🔹 قاعدة البيانات
DATABASE_URL = env("DATABASE_URL", default=None)
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": env("DB_ENGINE", default="django.db.backends.postgresql"),
            "NAME": env("DB_NAME", default="postgres"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="5432"),
            'APP_DIRS': True,
            'DIRS': [BASE_DIR / "templates"],
        }
    }

# 🔹 التحقق من الباسورد (سهل)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    }
]
# لو عايز تلغي الشروط كلها: AUTH_PASSWORD_VALIDATORS = []

# 🔹 اللغة والوقت
LANGUAGE_CODE = "ar"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# 🔹 الملفات الثابتة
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# 👇 أضف ده
STATICFILES_DIRS = [
    BASE_DIR / "static",   # ده اللي فيه img/ElAseel_logo_bw.png
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# 🔹 ملفات الميديا (لو بتستخدمها)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 🔹 باسورد افتراضي (اختياري)
DEFAULT_USER_PASSWORD = env("DEFAULT_USER_PASSWORD", default="12345678")
# عشان يوجّهك على /login/ بدل /accounts/login/
LOGIN_URL = '/login/'

# ممكن كمان تحدد الافتراضي بعد اللوجن
LOGIN_REDIRECT_URL = '/dashboard/'   # أو أي صفحة عايزها بعد نجاح اللوجن
LOGOUT_REDIRECT_URL = '/login/'      # بعد تسجيل الخروج يرجّع للوجن
