# Generated migration to make store and telephone fields optional

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0010_add_settled_at_field'),
    ]

    operations = [
        # 将store字段改为可选
        migrations.AlterField(
            model_name='submission',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='recycling.store', verbose_name='适用门店'),
        ),
        # 将telephone字段改为可选
        migrations.AlterField(
            model_name='submission',
            name='telephone',
            field=models.CharField(blank=True, max_length=20, verbose_name='联系电话'),
        ),
    ]