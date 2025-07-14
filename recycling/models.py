from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """卡券类别"""
    name = models.CharField(max_length=100, verbose_name='类别名称')
    
    class Meta:
        verbose_name = '卡券类别'
        verbose_name_plural = '卡券类别'
    
    def __str__(self):
        return self.name


class Store(models.Model):
    """门店"""
    name = models.CharField(max_length=100, verbose_name='门店名称')
    store_number = models.CharField(max_length=20, unique=True, verbose_name='门店编号')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '门店'
        verbose_name_plural = '门店'
        ordering = ['store_number']
    
    def __str__(self):
        return f"适用{self.store_number}店"


class Package(models.Model):
    """套餐"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='所属类别')
    name = models.CharField(max_length=100, verbose_name='套餐名称')
    commission = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='佣金')
    applicable_stores = models.ManyToManyField(Store, blank=True, verbose_name='适用门店')
    
    class Meta:
        verbose_name = '套餐'
        verbose_name_plural = '套餐'
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_store_names(self):
        """获取适用门店名称列表"""
        return [store.name for store in self.applicable_stores.all()]
    
    def get_store_display(self):
        """获取适用门店显示字符串"""
        stores = self.applicable_stores.all()
        if not stores:
            return "全店通用"
        return "、".join([str(store) for store in stores])


class Submission(models.Model):
    """提交记录"""
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('settled', '已结算'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='卡券类别')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, verbose_name='套餐')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name='适用门店')
    commission = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='佣金')
    card_number = models.CharField(max_length=200, blank=True, verbose_name='卡号')
    card_secret = models.CharField(max_length=200, blank=True, verbose_name='密码')
    image = models.URLField(blank=True, verbose_name='核销码图片')
    expire_date = models.DateField(verbose_name='过期时间')
    telephone = models.CharField(max_length=20, verbose_name='联系电话')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    admin_remark = models.TextField(blank=True, verbose_name='管理员备注')
    
    class Meta:
        verbose_name = '提交记录'
        verbose_name_plural = '提交记录'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.category.name} - {self.get_status_display()}"