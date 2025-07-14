"""
生产环境配置文件
使用方法：python manage.py runserver --settings=card_recycle.settings_production
"""

from .settings import *
import os

# 生产环境安全配置
DEBUG = False
ALLOWED_HOSTS = ['*']  # 请替换为您的实际域名

# 数据库配置 - 使用环境变量或修改为您的数据库信息
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'card_recycling'),
        'USER': os.environ.get('DB_USER', 'connect'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'your_password'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES',
        }
    }
}

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_collected')

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 安全配置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# 七牛云配置 - 生产环境请设置环境变量
QINIU_ACCESS_KEY = os.environ.get('QINIU_ACCESS_KEY', 'nfxmZVGEHjkd8Rsn44S-JSynTBUUguTScil9dDvC')
QINIU_SECRET_KEY = os.environ.get('QINIU_SECRET_KEY', 'your_secret_key')
QINIU_BUCKET_NAME = os.environ.get('QINIU_BUCKET_NAME', 'youxuan-images')
QINIU_BUCKET_DOMAIN = os.environ.get('QINIU_BUCKET_DOMAIN', 'https://guangpan.lingjing235.cn')