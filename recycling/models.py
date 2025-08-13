from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """卡券类别"""
    name = models.CharField(max_length=100, verbose_name='类别名称')
    show_store_field = models.BooleanField(default=True, verbose_name='显示门店选择字段')
    
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
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, verbose_name='适用门店')
    commission = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='佣金')
    card_number = models.CharField(max_length=200, blank=True, verbose_name='卡号')
    card_secret = models.CharField(max_length=200, blank=True, verbose_name='密码')
    redemption_code = models.CharField(max_length=200, blank=True, verbose_name='兑换码')
    image = models.URLField(blank=True, verbose_name='核销码图片')
    expire_date = models.DateField(verbose_name='过期时间')
    telephone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
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


class BottleCapSubmission(models.Model):
    """瓶盖提交记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    qr_codes = models.JSONField(verbose_name='瓶盖二维码图片列表', help_text='存储七牛云图片URL列表')
    payment_code = models.URLField(verbose_name='收款码图片', help_text='微信或支付宝收款码')
    is_settled = models.BooleanField(default=False, verbose_name='是否已结算')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    settled_at = models.DateTimeField(null=True, blank=True, verbose_name='结算时间')
    admin_remark = models.TextField(blank=True, verbose_name='管理员备注')
    
    class Meta:
        verbose_name = '瓶盖提交记录'
        verbose_name_plural = '瓶盖提交记录'
        ordering = ['-submitted_at']
    
    def __str__(self):
        status = '已结算' if self.is_settled else '待结算'
        return f"{self.user.username} - 瓶盖提交 - {status}"
    
    def get_qr_code_count(self):
        """获取瓶盖二维码数量"""
        return len(self.qr_codes) if self.qr_codes else 0


class Notification(models.Model):
    """系统通知模型"""
    title = models.CharField(max_length=200, verbose_name='通知标题')
    content = models.TextField(verbose_name='通知内容', help_text='支持HTML格式')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    target_page = models.CharField(
        max_length=50, 
        choices=[
            ('home', '首页'),
            ('bottle_cap', '瓶盖提交页面'),
            ('card_submit', '卡券提交页面'),
            ('all_pages', '所有页面'),
        ],
        default='home',
        verbose_name='显示页面'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '系统通知'
        verbose_name_plural = '系统通知'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'{self.title} - {"启用" if self.is_active else "停用"}'


class Tutorial(models.Model):
    """教程文章模型"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='教程标题')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='所属类别')
    content = models.TextField(verbose_name='教程内容', help_text='支持Markdown格式')
    summary = models.CharField(max_length=300, verbose_name='教程摘要')
    cover_image = models.URLField(blank=True, verbose_name='封面图片')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    is_featured = models.BooleanField(default=False, verbose_name='是否推荐')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    views = models.PositiveIntegerField(default=0, verbose_name='浏览次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    
    class Meta:
        verbose_name = '教程文章'
        verbose_name_plural = '教程文章'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'{self.title} - {self.get_status_display()}'
    
    def increment_views(self):
        """增加浏览次数"""
        self.views += 1
        self.save(update_fields=['views'])