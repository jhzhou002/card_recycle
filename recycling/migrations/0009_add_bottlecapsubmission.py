# Generated migration for BottleCapSubmission model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recycling', '0008_make_store_required'),
    ]

    operations = [
        migrations.CreateModel(
            name='BottleCapSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qr_codes', models.JSONField(help_text='存储七牛云图片URL列表', verbose_name='瓶盖二维码图片列表')),
                ('payment_code', models.URLField(help_text='微信或支付宝收款码', verbose_name='收款码图片')),
                ('is_settled', models.BooleanField(default=False, verbose_name='是否已结算')),
                ('admin_remark', models.TextField(blank=True, verbose_name='管理员备注')),
                ('submitted_at', models.DateTimeField(auto_now_add=True, verbose_name='提交时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '瓶盖提交',
                'verbose_name_plural': '瓶盖提交',
                'ordering': ['-submitted_at'],
            },
        ),
    ]