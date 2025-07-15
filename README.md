# 卡券回收平台

一个基于Django 4.2的卡券回收管理平台，用户可以提交闲置卡券信息进行回收，管理员可以审核处理提交记录。

## 🚀 项目特色

- **用户友好**: 响应式设计，支持移动端和桌面端
- **多级分类**: 卡券类别 → 套餐 → 适用门店的三级选择
- **图片上传**: 支持七牛云对象存储，安全高效
- **状态跟踪**: 完整的审核流程和状态管理
- **现代UI**: Bootstrap 5 + 自定义样式，界面美观
- **安全认证**: 图片验证码 + Django内置认证系统

## 📋 技术栈

### 后端技术
- **框架**: Django 4.2 + Django REST Framework
- **数据库**: MySQL 8.x
- **认证**: Django内置认证系统
- **图片处理**: Pillow (PIL)

### 前端技术
- **样式框架**: Bootstrap 5
- **图标**: Font Awesome 6.0
- **交互**: jQuery 3.6
- **设计**: 响应式布局，渐变色彩

### 云服务
- **对象存储**: 七牛云
- **部署**: 支持宝塔面板 + Nginx + Gunicorn

## 🏗️ 项目架构

### 数据模型
```
Category (卡券类别)
├── Package (套餐)
│   └── Store (适用门店) [多对多关系]
└── Submission (提交记录)
    ├── 关联用户
    ├── 关联套餐
    ├── 关联门店
    └── 图片URL (七牛云)
```

### 核心功能模块
- **用户模块**: 注册、登录、个人中心
- **提交模块**: 卡券信息提交、图片上传
- **审核模块**: 管理员审核、状态更新
- **统计模块**: 仪表板数据展示

## 📦 安装部署

### 环境要求
- Python 3.8+
- MySQL 8.0+
- Redis (可选，用于缓存)

### 快速开始

1. **克隆项目**
```bash
git clone https://github.com/jhzhou002/card_recycle.git
cd card_recycle
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置数据库**
```python
# 在 settings.py 中配置数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'card_recycling',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

4. **配置七牛云**
```python
# 在 settings.py 中配置七牛云
QINIU_ACCESS_KEY = 'your_access_key'
QINIU_SECRET_KEY = 'your_secret_key'
QINIU_BUCKET_NAME = 'your_bucket'
QINIU_BUCKET_DOMAIN = 'https://your-domain.com'
```

5. **数据库迁移**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

6. **收集静态文件**
```bash
python manage.py collectstatic
```

7. **运行开发服务器**
```bash
python manage.py runserver
```

### 生产部署

详细的宝塔面板部署说明请参考 [DEPLOYMENT.md](DEPLOYMENT.md)

## 🎯 核心功能

### 用户功能
- ✅ **用户注册/登录**: 图片验证码验证
- ✅ **卡券提交**: 三级分类选择 + 图片上传
- ✅ **个人记录**: 查看提交历史和状态
- ✅ **实时跟踪**: 审核状态实时更新

### 管理员功能
- ✅ **仪表板**: 统计数据可视化
- ✅ **审核管理**: 批量处理提交记录
- ✅ **状态更新**: 通过/拒绝/结算
- ✅ **备注管理**: 添加审核备注

### API接口
- `GET /api/packages/` - 根据类别获取套餐列表
- `GET /api/stores/` - 根据套餐获取门店列表
- `GET /api/qiniu-token/` - 获取七牛云上传token
- `POST /api/upload-image/` - 上传图片到七牛云
- `GET /api/refresh-captcha/` - 刷新验证码

## 📱 界面预览

### 登录页面
- 现代化渐变设计
- 图片验证码验证
- 响应式布局

### 提交页面
- 三级联动选择
- 拖拽上传图片
- 实时进度显示

### 管理后台
- 数据统计图表
- 批量操作功能
- 状态管理工具

## 🔧 开发指南

### 目录结构
```
card_recycle/
├── card_recycle/          # 项目配置
│   ├── settings.py        # 主配置文件
│   ├── settings_production.py  # 生产环境配置
│   ├── urls.py           # 主URL配置
│   └── wsgi.py           # WSGI配置
├── recycling/            # 主应用
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── forms.py          # 表单定义
│   ├── urls.py           # 应用URL配置
│   └── admin.py          # 管理后台配置
├── templates/            # 模板文件
│   └── recycling/        # 应用模板
├── static/              # 静态文件
│   ├── css/             # 样式文件
│   ├── js/              # JavaScript文件
│   └── webfonts/        # 字体文件
├── utils/               # 工具类
│   ├── qiniu_util.py    # 七牛云工具
│   └── captcha.py       # 验证码生成
└── manage.py            # Django管理脚本
```

### 数据模型说明

#### Category (卡券类别)
```python
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='类别名称')
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Package (套餐)
```python
class Package(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='套餐名称')
    commission = models.DecimalField(max_digits=10, decimal_places=2)
    stores = models.ManyToManyField(Store, verbose_name='适用门店')
```

#### Store (门店)
```python
class Store(models.Model):
    name = models.CharField(max_length=100, verbose_name='门店名称')
    store_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
```

#### Submission (提交记录)
```python
class Submission(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('settled', '已结算'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
```

### 状态流程图
```
提交记录生命周期:
[用户提交] → [待审核] → [已通过/已拒绝] → [已结算]
                ↓
          [管理员审核]
```

## 🎨 自定义开发

### 添加新的卡券类别
1. 在管理后台添加 Category
2. 添加相关的 Package
3. 配置适用的 Store

### 修改验证码样式
编辑 `utils/captcha.py`:
```python
def generate_captcha_image(text, width=200, height=80):
    # 自定义验证码生成逻辑
    pass
```

### 自定义主题样式
编辑 `templates/recycling/base.html` 中的 CSS:
```css
/* 自定义主题颜色 */
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
}
```

## 🔒 安全特性

- **CSRF保护**: Django内置CSRF令牌
- **用户认证**: 基于会话的认证系统
- **权限控制**: 管理员权限分离
- **图片验证码**: 防止自动化攻击
- **文件上传安全**: 七牛云安全存储
- **SQL注入防护**: Django ORM保护

## 📊 性能优化

- **静态文件**: 本地化CSS/JS文件，减少CDN依赖
- **数据库**: 合理的索引和外键设计
- **图片存储**: 七牛云CDN加速
- **缓存策略**: 支持Redis缓存(可选)
- **代码优化**: 查询优化和N+1问题避免

## 🐛 常见问题

### 验证码显示问题
确保服务器安装了字体文件:
```bash
sudo apt-get install fonts-dejavu-core
```

### 静态文件404
手动下载静态文件到static目录:
```bash
cd static
wget https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css -P css/
wget https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css -P css/
```

### 数据库迁移错误
重置迁移文件:
```bash
python manage.py migrate --fake recycling zero
python manage.py makemigrations recycling
python manage.py migrate
```

## 📝 更新日志

### v1.0.0 (2024-01-15)
- ✨ 初始版本发布
- ✨ 用户注册登录功能
- ✨ 卡券提交功能
- ✨ 管理员审核功能

### v1.1.0 (2024-01-20)
- ✨ 添加门店选择功能
- 🐛 修复验证码显示问题
- 🔧 优化静态文件加载
- 📚 完善部署文档

### v1.2.0 (2025-01-15)
- 🐛 彻底修复验证码字符大小问题
- 🔧 本地化静态资源，优化加载速度
- 📱 增强移动端响应式体验
- 🎨 优化验证码生成算法

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 开源协议

本项目采用 MIT 协议 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **开发者**: Claude Code Assistant
- **维护者**: [jhzhou002](https://github.com/jhzhou002)

## 🙏 致谢

- Django 框架团队
- Bootstrap 团队
- 七牛云技术支持
- 所有贡献者

---

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**