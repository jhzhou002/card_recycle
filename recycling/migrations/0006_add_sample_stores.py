# Generated migration to add sample store data

from django.db import migrations


def create_sample_stores(apps, schema_editor):
    """创建示例门店数据"""
    Store = apps.get_model('recycling', 'Store')
    
    sample_stores = [
        {'name': '7号门店', 'store_number': '7'},
        {'name': '12号门店', 'store_number': '12'},
        {'name': '15号门店', 'store_number': '15'},
        {'name': '20号门店', 'store_number': '20'},
        {'name': '25号门店', 'store_number': '25'},
        {'name': '30号门店', 'store_number': '30'},
    ]
    
    for store_data in sample_stores:
        Store.objects.get_or_create(
            store_number=store_data['store_number'],
            defaults={'name': store_data['name']}
        )


def reverse_create_sample_stores(apps, schema_editor):
    """删除示例门店数据"""
    Store = apps.get_model('recycling', 'Store')
    Store.objects.filter(store_number__in=['7', '12', '15', '20', '25', '30']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('recycling', '0005_add_store_model'),
    ]

    operations = [
        migrations.RunPython(create_sample_stores, reverse_create_sample_stores),
    ]