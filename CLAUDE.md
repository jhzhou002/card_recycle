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
```

### 数据库操作
```bash
# 重置数据库
python manage.py flush

# 导入初始数据
python manage.py loaddata fixtures/initial_data.json

# 收集静态文件
python manage.py collectstatic
```

## 核心架构

### 数据模型
- **Category**: 卡券类别 (id, name)
- **Package**: 套餐 (id, category_id, name, commission)
- **Submission**: 提交记录 (用户提交的卡券信息，包含状态跟踪)

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

### API接口
- `/api/packages/` - 根据类别获取套餐
- `/api/qiniu-token/` - 获取七牛云上传token
- `/api/upload-image/` - 上传图片到七牛云

## 开发注意事项

1. **图片上传**: 使用七牛云存储，前端上传前需要获取token
2. **状态管理**: 提交记录状态变更需要管理员权限
3. **权限控制**: 管理员功能使用 `@staff_member_required` 装饰器
4. **响应式设计**: 使用Bootstrap确保移动端兼容

## 部署信息

- **Web服务器**: Nginx
- **应用服务器**: Gunicorn
- **部署工具**: 宝塔面板