from django import forms
from .models import Submission, Category, Package


class SubmissionForm(forms.ModelForm):
    """卡券提交表单"""
    
    class Meta:
        model = Submission
        fields = ['category', 'package', 'card_number', 'card_secret', 'image', 'expire_date', 'telephone']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'category'}),
            'package': forms.Select(attrs={'class': 'form-control', 'id': 'package'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入卡号'}),
            'card_secret': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入密码'}),
            'image': forms.HiddenInput(),
            'expire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入联系电话'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = Package.objects.none()
        
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['package'].queryset = Package.objects.filter(category_id=category_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['package'].queryset = self.instance.category.package_set.all()
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        package = cleaned_data.get('package')
        
        if category and package:
            if package.category != category:
                raise forms.ValidationError('选择的套餐不属于该类别')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # 设置佣金
        if instance.package:
            instance.commission = instance.package.commission
        if commit:
            instance.save()
        return instance