from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('submit/', views.submit_card, name='submit_card'),
    path('my-submissions/', views.my_submissions, name='my_submissions'),
    path('submission/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('api/packages/', views.get_packages, name='get_packages'),
    path('api/stores/', views.get_stores, name='get_stores'),
    path('api/qiniu-token/', views.get_qiniu_token, name='get_qiniu_token'),
    path('api/refresh-captcha/', views.refresh_captcha, name='refresh_captcha'),
    
    # 瓶盖相关路由
    path('submit-bottle-cap/', views.submit_bottle_cap, name='submit_bottle_cap'),
    path('my-bottle-caps/', views.my_bottle_caps, name='my_bottle_caps'),
    
    # 管理员路由
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-submissions/', views.admin_submissions, name='admin_submissions'),
    path('admin-submissions/<int:submission_id>/update/', views.admin_update_submission, name='admin_update_submission'),
    path('admin-submissions/<int:submission_id>/detail/', views.admin_submission_detail, name='admin_submission_detail'),
    
    # 管理员瓶盖管理路由
    path('admin-bottle-caps/', views.admin_bottle_caps, name='admin_bottle_caps'),
    path('admin-bottle-caps/<int:bottle_cap_id>/update/', views.admin_update_bottle_cap, name='admin_update_bottle_cap'),
    path('admin-bottle-caps/<int:bottle_cap_id>/detail/', views.admin_bottle_cap_detail, name='admin_bottle_cap_detail'),
    path('admin-bottle-caps/batch-update/', views.admin_bottle_caps_batch_update, name='admin_bottle_caps_batch_update'),
    path('admin-bottle-caps/export-pdf/', views.export_bottle_caps_pdf, name='export_bottle_caps_pdf'),
    path('admin-bottle-caps/export-web/', views.export_bottle_caps_web, name='export_bottle_caps_web'),
    path('admin-bottle-caps/export-with-payment/', views.export_bottle_caps_with_payment, name='export_bottle_caps_with_payment'),
    path('admin-bottle-caps/export-images/', views.export_bottle_caps_images, name='export_bottle_caps_images'),
    
    # 通知管理路由
    path('admin-notifications/', views.admin_notifications, name='admin_notifications'),
    path('admin-notifications/add/', views.admin_notification_edit, name='admin_notification_add'),
    path('admin-notifications/<int:notification_id>/edit/', views.admin_notification_edit, name='admin_notification_edit'),
    path('admin-notifications/<int:notification_id>/delete/', views.admin_notification_delete, name='admin_notification_delete'),
    
    # 卡券类别管理路由
    path('admin-categories/', views.admin_categories, name='admin_categories'),
    
    # 套餐管理路由
    path('admin-packages/', views.admin_packages, name='admin_packages'),
    
    # 门店管理路由
    path('admin-stores/', views.admin_stores, name='admin_stores'),
]