# Generated migration for URLField change

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0003_update_image_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='image',
            field=models.URLField(blank=True, verbose_name='核销码图片'),
        ),
    ]