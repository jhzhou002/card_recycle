# Add missing settled_at field to BottleCapSubmission

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0009_add_bottlecapsubmission'),
    ]

    operations = [
        migrations.AddField(
            model_name='bottlecapsubmission',
            name='settled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='结算时间'),
        ),
    ]