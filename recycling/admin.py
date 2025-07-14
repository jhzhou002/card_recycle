from django.contrib import admin
from .models import Category, Package, Submission


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'name', 'commission']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'package', 'commission', 'status', 'submitted_at']
    list_filter = ['status', 'category', 'submitted_at']
    search_fields = ['user__username', 'card_number', 'telephone']
    readonly_fields = ['submitted_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'category', 'package', 'commission')
        }),
        ('卡券信息', {
            'fields': ('card_number', 'card_secret', 'image', 'expire_date', 'telephone')
        }),
        ('状态管理', {
            'fields': ('status', 'admin_remark')
        }),
        ('时间信息', {
            'fields': ('submitted_at', 'updated_at')
        }),
    )