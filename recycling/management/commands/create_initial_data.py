from django.core.management.base import BaseCommand
from recycling.models import Category, Package


class Command(BaseCommand):
    help = '创建初始数据'

    def handle(self, *args, **options):
        # 创建卡券类别
        categories_data = [
            '购物卡',
            '餐饮卡',
            '加油卡',
            '游戏卡',
            '话费卡',
            '视频会员卡',
        ]
        
        for category_name in categories_data:
            category, created = Category.objects.get_or_create(name=category_name)
            if created:
                self.stdout.write(f'创建类别: {category_name}')
        
        # 创建套餐
        packages_data = [
            ('购物卡', '100元购物卡', 8.00),
            ('购物卡', '200元购物卡', 16.00),
            ('购物卡', '500元购物卡', 40.00),
            ('餐饮卡', '100元餐饮卡', 7.50),
            ('餐饮卡', '200元餐饮卡', 15.00),
            ('加油卡', '100元加油卡', 9.00),
            ('加油卡', '200元加油卡', 18.00),
            ('加油卡', '500元加油卡', 45.00),
            ('游戏卡', '50元游戏卡', 4.50),
            ('游戏卡', '100元游戏卡', 9.00),
            ('话费卡', '50元话费卡', 4.80),
            ('话费卡', '100元话费卡', 9.50),
            ('视频会员卡', '1个月会员', 5.00),
            ('视频会员卡', '3个月会员', 15.00),
            ('视频会员卡', '12个月会员', 50.00),
        ]
        
        for category_name, package_name, commission in packages_data:
            try:
                category = Category.objects.get(name=category_name)
                package, created = Package.objects.get_or_create(
                    category=category,
                    name=package_name,
                    defaults={'commission': commission}
                )
                if created:
                    self.stdout.write(f'创建套餐: {category_name} - {package_name}')
            except Category.DoesNotExist:
                self.stdout.write(f'类别不存在: {category_name}')
        
        self.stdout.write(self.style.SUCCESS('初始数据创建完成!'))