# Generated migration for Store model and Package updates

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0004_update_image_to_urlfield'),
    ]

    operations = [
        # 创建Store表
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='门店名称')),
                ('store_number', models.CharField(max_length=20, unique=True, verbose_name='门店编号')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '门店',
                'verbose_name_plural': '门店',
                'ordering': ['store_number'],
            },
        ),
        
        # 为Package表添加applicable_stores字段
        migrations.AddField(
            model_name='package',
            name='applicable_stores',
            field=models.ManyToManyField(blank=True, to='recycling.Store', verbose_name='适用门店'),
        ),
        
        # 为Submission表添加store字段
        migrations.AddField(
            model_name='submission',
            name='store',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='recycling.store', verbose_name='适用门店'),
            preserve_default=False,
        ),
    ]