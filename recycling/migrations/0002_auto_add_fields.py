# Generated migration for adding new fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='show_store_field',
            field=models.BooleanField(default=True, verbose_name='显示门店选择字段'),
        ),
        migrations.AddField(
            model_name='submission',
            name='redemption_code',
            field=models.CharField(blank=True, max_length=200, verbose_name='兑换码'),
        ),
    ]