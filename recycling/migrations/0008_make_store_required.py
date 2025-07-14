# Generated migration to make store field required

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0007_update_existing_submissions'),
    ]

    operations = [
        # 将store字段改为必填
        migrations.AlterField(
            model_name='submission',
            name='store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recycling.store', verbose_name='适用门店'),
        ),
    ]