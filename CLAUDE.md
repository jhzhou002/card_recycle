# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于Django 4.2的卡券回收平台，用户可以提交闲置卡券信息进行回收，管理员可以审核处理提交记录。

## 技术栈

- **后端**: Django 4.2 + Django REST Framework
- **前端**: Bootstrap 5 + jQuery
- **数据库**: MySQL 8.x
- **云存储**: 七牛云对象存储
- **认证**: Django内置认证系统

## 常用命令

### 开发环境设置
```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 运行开发服务器
python manage.py runserver

# 创建初始测试数据
python manage.py create_initial_data
```

### 数据库操作
```bash
# 重置数据库
python manage.py flush

# 收集静态文件
python manage.py collectstatic

# 生产环境使用特定配置
python manage.py runserver --settings=card_recycle.settings_production
```

### 调试和测试
```bash
# 进入Django shell
python manage.py shell

# 检查项目配置
python manage.py check

# 查看数据库迁移状态
python manage.py showmigrations
```

## 核心架构

### 数据模型关系
```
Category (卡券类别)
├── show_store_field (控制是否显示门店选择)
└── Package (套餐)
    ├── commission (佣金金额)
    └── applicable_stores (多对多关联门店)

Store (门店)
├── store_number (唯一编号)
└── is_active (启用状态)

User (用户)
├── Submission (卡券提交记录)
│   ├── status: pending → approved/rejected → settled
│   └── admin_remark (管理员备注)
└── BottleCapSubmission (瓶盖提交记录)
    ├── qr_codes (JSON格式存储图片列表)
    └── payment_code (收款码图片)

Notification (系统通知)
├── target_page (显示页面控制)
└── content (支持HTML格式)

Tutorial (教程文章)
├── status: draft → published → archived
├── content (Markdown格式)
└── views (浏览次数统计)
```

### 用户角色
- **普通用户**: 提交卡券回收申请，查看个人提交记录
- **管理员**: 审核提交记录，更新状态，添加备注

### 状态流程
提交记录状态：待审核 -> 已通过/已拒绝 -> 已结算

## 项目结构

```
card_recycle/
├── card_recycle/          # 项目配置
│   ├── settings.py        # 包含数据库和七牛云配置
│   ├── urls.py           # 主URL配置
│   └── wsgi.py           # WSGI配置
├── recycling/            # 主应用
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── forms.py          # 表单
│   ├── urls.py           # 应用URL配置
│   └── admin.py          # 管理后台配置
├── templates/            # 模板文件
│   └── recycling/
├── static/              # 静态文件
│   ├── css/
│   └── js/
├── utils/               # 工具类
│   └── qiniu_util.py    # 七牛云上传工具
└── manage.py            # Django管理脚本
```

## 重要配置

### 数据库配置
- 主机: 8.153.77.15
- 数据库: card_recycling
- 用户: connect
- 字符集: utf8mb4

### 七牛云配置
- 存储空间: youxuan-images
- 域名: https://guangpan.lingjing235.cn
- 文件上传路径: card_recycle/

## 关键功能

### 用户功能
- 用户注册/登录
- 卡券提交（支持图片上传）
- 个人记录查看
- 状态实时跟踪

### 管理员功能
- 仪表板统计
- 审核提交记录
- 状态更新
- 备注管理

### 关键API接口
- `GET /api/categories/` - 获取所有卡券类别
- `GET /api/packages/?category_id=<id>` - 根据类别获取套餐列表
- `GET /api/stores/?package_id=<id>` - 根据套餐获取适用门店
- `GET /api/qiniu-token/` - 获取七牛云上传token (需要登录)
- `POST /api/refresh-captcha/` - 刷新验证码

## 开发注意事项

### 关键技术点
1. **图片上传流程**: 
   - 前端获取七牛云token (`/api/qiniu-token/`)
   - 直接上传到七牛云服务器
   - 返回图片URL存储在数据库中

2. **权限控制系统**:
   - 用户功能: `@login_required` 装饰器
   - 管理员功能: `@staff_member_required` 装饰器
   - 管理员登录后自动跳转到管理后台

3. **验证码机制**: 
   - 数学运算验证码存储在session中
   - 使用自定义验证码生成工具 (`utils/captcha.py`)

4. **双提交系统**:
   - 卡券提交 (Submission模型) - 传统卡券回收
   - 瓶盖提交 (BottleCapSubmission模型) - 多图片瓶盖回收

### 重要配置文件
- `settings.py` - 开发环境配置
- `settings_production.py` - 生产环境配置
- `nginx.conf` - Nginx配置模板

## 部署信息

- **Web服务器**: Nginx
- **应用服务器**: Gunicorn
- **部署工具**: 宝塔面板