# CSRF问题修复说明

## 问题描述
访问 `https://card.lingjing235.cn` 时出现CSRF验证失败错误：
```
Origin checking failed - https://card.lingjing235.cn does not match any trusted origins.
```

## 解决方案

### 1. 更新Django配置
已在 `settings_production.py` 中添加以下配置：

```python
# 允许的主机
ALLOWED_HOSTS = [
    'card.lingjing235.cn',
    'localhost',
    '127.0.0.1',
    '8.153.77.15',  # 服务器IP
]

# CSRF可信任来源
CSRF_TRUSTED_ORIGINS = [
    'https://card.lingjing235.cn',
    'http://card.lingjing235.cn',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# CSRF Cookie设置
CSRF_COOKIE_SECURE = False  # HTTP使用False，HTTPS使用True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Session Cookie设置
SESSION_COOKIE_SECURE = False  # HTTP使用False，HTTPS使用True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

### 2. 部署步骤

1. **确保使用生产配置文件**：
   ```bash
   # 在宝塔Python项目设置中，确保启动命令使用生产配置
   python manage.py runserver --settings=card_recycle.settings_production
   # 或使用环境变量
   export DJANGO_SETTINGS_MODULE=card_recycle.settings_production
   ```

2. **重启应用**：
   ```bash
   # 在宝塔面板中重启Python项目
   # 或手动重启Gunicorn进程
   ```

3. **验证配置**：
   - 访问 `https://card.lingjing235.cn`
   - 测试登录功能
   - 确认CSRF验证通过

### 3. HTTPS支持

如果您的域名使用HTTPS，需要将以下设置改为True：
```python
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

### 4. 调试信息

如果问题仍然存在，可以临时启用调试模式检查：
```python
DEBUG = True  # 仅用于调试，生产环境请设为False
```

然后查看详细的错误信息。

## 安全注意事项

1. **生产环境**必须设置 `DEBUG = False`
2. **HTTPS环境**必须设置 `*_SECURE = True`
3. **域名限制**：`ALLOWED_HOSTS` 应仅包含真实使用的域名
4. **定期更新**：定期检查和更新安全配置

## 常见问题

### Q: 仍然出现CSRF错误
A: 检查以下项目：
- 确认域名配置正确
- 重启Django应用
- 清除浏览器缓存和Cookie
- 检查Nginx配置中的proxy_set_header

### Q: 本地开发正常，生产环境出错
A: 确认使用了正确的配置文件（settings_production.py）

### Q: HTTPS证书问题
A: 检查域名SSL证书是否正确配置，必要时联系服务商