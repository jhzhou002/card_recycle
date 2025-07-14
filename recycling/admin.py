from django.contrib import admin
from .models import Category, Package, Submission, Store


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'store_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'store_number']
    ordering = ['store_number']


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'name', 'commission', 'get_store_display']
    list_filter = ['category', 'applicable_stores']
    search_fields = ['name']
    filter_horizontal = ['applicable_stores']
    
    def get_store_display(self, obj):
        return obj.get_store_display()
    get_store_display.short_description = '适用门店'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'package', 'store', 'commission', 'status', 'submitted_at']
    list_filter = ['status', 'category', 'store', 'submitted_at']
    search_fields = ['user__username', 'card_number', 'telephone']
    readonly_fields = ['submitted_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'category', 'package', 'store', 'commission')
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