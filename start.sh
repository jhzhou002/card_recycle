#!/bin/bash

# 卡券回收平台启动脚本

# 设置项目路径
PROJECT_PATH="/www/wwwroot/card_recycle"
cd $PROJECT_PATH

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 设置环境变量
export DJANGO_SETTINGS_MODULE=card_recycle.settings_production

# 数据库迁移
echo "正在执行数据库迁移..."
python manage.py migrate --settings=card_recycle.settings_production

# 收集静态文件
echo "正在收集静态文件..."
python manage.py collectstatic --noinput --settings=card_recycle.settings_production

# 启动Gunicorn服务器
echo "启动Django服务器..."
gunicorn --bind 127.0.0.1:8000 --workers 3 --worker-class gevent card_recycle.wsgi:application