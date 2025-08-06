from django import forms
from .models import Submission, Category, Package, Store, BottleCapSubmission


class SubmissionForm(forms.ModelForm):
    """卡券提交表单"""
    
    class Meta:
        model = Submission
        fields = ['category', 'package', 'store', 'card_number', 'card_secret', 'redemption_code', 'image', 'expire_date', 'telephone']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'category'}),
            'package': forms.Select(attrs={'class': 'form-control', 'id': 'package'}),
            'store': forms.Select(attrs={'class': 'form-control', 'id': 'store'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入卡号（可选）'}),
            'card_secret': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入密码（可选）'}),
            'redemption_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入兑换码（可选）'}),
            'image': forms.HiddenInput(),
            'expire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入联系电话'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = Package.objects.none()
        self.fields['store'].queryset = Store.objects.none()
        
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                category = Category.objects.get(id=category_id)
                
                # 根据类别控制门店字段是否显示
                if not category.show_store_field:
                    self.fields['store'].widget = forms.HiddenInput()
                    self.fields['store'].required = False
                
                self.fields['package'].queryset = Package.objects.filter(category_id=category_id)
                
                # 如果已选择套餐，加载对应的门店
                if 'package' in self.data:
                    try:
                        package_id = int(self.data.get('package'))
                        package = Package.objects.get(id=package_id)
                        if package.applicable_stores.exists():
                            self.fields['store'].queryset = package.applicable_stores.filter(is_active=True)
                        else:
                            # 如果套餐没有指定门店，显示所有活跃门店
                            self.fields['store'].queryset = Store.objects.filter(is_active=True)
                    except (ValueError, TypeError, Package.DoesNotExist):
                        pass
                        
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            # 根据现有实例的类别控制门店字段显示
            if self.instance.category and not self.instance.category.show_store_field:
                self.fields['store'].widget = forms.HiddenInput()
                self.fields['store'].required = False
                
            self.fields['package'].queryset = self.instance.category.package_set.all()
            if self.instance.package and self.instance.package.applicable_stores.exists():
                self.fields['store'].queryset = self.instance.package.applicable_stores.filter(is_active=True)
            else:
                self.fields['store'].queryset = Store.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        package = cleaned_data.get('package')
        store = cleaned_data.get('store')
        card_number = cleaned_data.get('card_number', '').strip()
        card_secret = cleaned_data.get('card_secret', '').strip()
        redemption_code = cleaned_data.get('redemption_code', '').strip()
        image = cleaned_data.get('image')
        
        # 验证套餐是否属于选择的类别
        if category and package:
            if package.category != category:
                raise forms.ValidationError('选择的套餐不属于该类别')
        
        # 验证门店是否适用于选择的套餐（仅当类别显示门店字段时）
        if category and category.show_store_field and package and store:
            if package.applicable_stores.exists() and store not in package.applicable_stores.all():
                raise forms.ValidationError('选择的门店不适用于该套餐')
        
        # 验证至少要有卡号密码、兑换码或图片中的一个
        if not card_number and not card_secret and not redemption_code and not image:
            raise forms.ValidationError('请至少填写卡号密码、兑换码或上传核销码图片')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # 设置佣金
        if instance.package:
            instance.commission = instance.package.commission
        if commit:
            instance.save()
        return instance


class BottleCapSubmissionForm(forms.Form):
    """瓶盖提交表单"""
    qr_code_images = forms.FileField(
        label='瓶盖二维码',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        }),
        help_text='支持上传多张瓶盖二维码图片（JPG、PNG格式）'
    )
    
    payment_code_image = forms.ImageField(
        label='收款码',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text='上传微信或支付宝收款码图片'
    )
    
    def clean_qr_code_images(self):
        """验证瓶盖二维码图片"""
        # 由于这是多文件上传，在视图中处理
        return self.cleaned_data.get('qr_code_images')
    
    def clean_payment_code_image(self):
        """验证收款码图片"""
        image = self.cleaned_data.get('payment_code_image')
        if image:
            # 验证文件大小（最大10MB）
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('收款码图片大小不能超过10MB')
            
            # 验证文件类型
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError('请上传有效的图片文件')
        
        return image