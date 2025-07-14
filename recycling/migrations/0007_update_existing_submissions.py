# Generated migration to update existing submissions and make store field required

from django.db import migrations, models
import django.db.models.deletion


def update_existing_submissions(apps, schema_editor):
    """为现有的Submission记录设置默认门店"""
    Submission = apps.get_model('recycling', 'Submission')
    Store = apps.get_model('recycling', 'Store')
    
    # 获取默认门店（ID=1）
    try:
        default_store = Store.objects.get(id=1)
        # 更新所有没有门店的提交记录
        Submission.objects.filter(store__isnull=True).update(store=default_store)
    except Store.DoesNotExist:
        # 如果没有默认门店，创建一个
        default_store = Store.objects.create(
            id=1,
            name='默认门店',
            store_number='1',
            is_active=True
        )
        Submission.objects.filter(store__isnull=True).update(store=default_store)


def reverse_update_existing_submissions(apps, schema_editor):
    """回滚操作：将现有Submission的store字段设为空"""
    Submission = apps.get_model('recycling', 'Submission')
    Submission.objects.filter(store_id=1).update(store=None)


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0006_add_sample_stores'),
    ]

    operations = [
        # 1. 更新现有的Submission记录
        migrations.RunPython(update_existing_submissions, reverse_update_existing_submissions),
        
        # 2. 将store字段改为必填
        migrations.AlterField(
            model_name='submission',
            name='store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recycling.store', verbose_name='适用门店'),
        ),
    ]