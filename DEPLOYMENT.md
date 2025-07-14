# 🚀 宝塔部署指南

## 1. 服务器准备

### 1.1 安装宝塔面板
```bash
# CentOS/RHEL
yum install -y wget && wget -O install.sh http://download.bt.cn/install/install_6.0.sh && sh install.sh

# Ubuntu/Debian  
wget -O install.sh http://download.bt.cn/install/install-ubuntu_6.0.sh && sudo bash install.sh
```

### 1.2 安装必要组件
在宝塔面板中安装：
- **Nginx 1.22+**
- **MySQL 8.0**
- **Python项目管理器**
- **PM2管理器**

## 2. 项目部署

### 2.1 上传项目文件
1. 在宝塔面板创建网站，根目录设为：`/www/wwwroot/card_recycle`
2. 将项目文件上传到该目录
3. 或者使用Git克隆：
```bash
cd /www/wwwroot/
git clone https://github.com/jhzhou002/card_recycle.git
```

### 2.2 Python环境配置
```bash
cd /www/wwwroot/card_recycle

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2.3 数据库配置
1. 在宝塔面板创建MySQL数据库：
   - 数据库名：`card_recycling`
   - 用户名：`connect`（或自定义）
   - 密码：设置强密码

2. 设置环境变量或修改 `settings_production.py`：
```bash
export DB_PASSWORD="your_database_password"
export QINIU_SECRET_KEY="your_qiniu_secret_key"
```

### 2.4 初始化项目
```bash
# 设置执行权限
chmod +x start.sh

# 执行数据库迁移
python manage.py migrate --settings=card_recycle.settings_production

# 创建超级用户
python manage.py createsuperuser --settings=card_recycle.settings_production

# 收集静态文件
python manage.py collectstatic --noinput --settings=card_recycle.settings_production
```

## 3. 进程管理

### 3.1 使用PM2管理Django进程
1. 在宝塔面板 → PM2管理器 → 添加项目
2. 项目配置：
   - **项目名称**：card_recycle
   - **启动文件**：start.sh
   - **项目目录**：/www/wwwroot/card_recycle
   - **启动模式**：bash

### 3.2 手动启动（备选方案）
```bash
cd /www/wwwroot/card_recycle
nohup gunicorn --bind 127.0.0.1:8000 --workers 3 card_recycle.wsgi:application > gunicorn.log 2>&1 &
```

## 4. Nginx配置

### 4.1 网站配置
1. 宝塔面板 → 网站 → 设置 → 配置文件
2. 替换为 `nginx.conf` 中的配置
3. 修改域名为您的实际域名

### 4.2 SSL证书（推荐）
1. 宝塔面板 → 网站 → SSL
2. 申请Let's Encrypt免费证书
3. 开启强制HTTPS

## 5. 安全配置

### 5.1 防火墙设置
- 开放端口：80, 443, 22, 8888（宝塔）
- 关闭端口：8000（Django内部端口）

### 5.2 定期备份
1. 宝塔面板 → 计划任务
2. 设置数据库自动备份
3. 设置网站文件自动备份

## 6. 监控和日志

### 6.1 查看日志
```bash
# Django日志
tail -f /www/wwwroot/card_recycle/django.log

# Nginx日志
tail -f /www/wwwlogs/yourdomain.com.log

# Gunicorn日志
tail -f /www/wwwroot/card_recycle/gunicorn.log
```

### 6.2 性能监控
- 使用宝塔监控插件
- 配置邮件/短信告警

## 7. 常见问题

### 7.1 静态文件404
```bash
python manage.py collectstatic --noinput --settings=card_recycle.settings_production
```

### 7.2 数据库连接失败
检查数据库配置和防火墙设置

### 7.3 权限问题
```bash
chown -R www:www /www/wwwroot/card_recycle
chmod -R 755 /www/wwwroot/card_recycle
```

## 8. 域名和DNS

1. 购买域名并解析到服务器IP
2. 在 `settings_production.py` 中更新 `ALLOWED_HOSTS`
3. 更新Nginx配置中的 `server_name`

## 🎉 部署完成

访问您的域名即可看到卡券回收平台正常运行！

管理后台地址：`https://yourdomain.com/admin/`