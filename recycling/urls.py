from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('submit/', views.submit_card, name='submit_card'),
    path('my-submissions/', views.my_submissions, name='my_submissions'),
    path('api/packages/', views.get_packages, name='get_packages'),
    path('api/qiniu-token/', views.get_qiniu_token, name='get_qiniu_token'),
    path('api/upload-image/', views.upload_image, name='upload_image'),
    
    # 管理员路由
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-submissions/', views.admin_submissions, name='admin_submissions'),
    path('admin-submissions/<int:submission_id>/update/', views.admin_update_submission, name='admin_update_submission'),
    path('admin-submissions/<int:submission_id>/detail/', views.admin_submission_detail, name='admin_submission_detail'),
]