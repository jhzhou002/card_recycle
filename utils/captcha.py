import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os


def generate_captcha_text(length=4):
    """生成验证码文本"""
    chars = string.ascii_uppercase + string.digits
    # 排除容易混淆的字符
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '').replace('L', '')
    return ''.join(random.choice(chars) for _ in range(length))


def get_best_font(target_size=48):
    """获取最佳字体，确保字体足够大"""
    try:
        # Linux系统字体路径（优先使用粗体）
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',     # Linux DejaVu Bold
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',         # Linux DejaVu
            '/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf',       # Ubuntu Mono Bold
            '/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf',       # Ubuntu Mono
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',  # Liberation Bold
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Liberation
            '/System/Library/Fonts/Arial.ttf',                        # macOS
            'C:/Windows/Fonts/arial.ttf',                             # Windows
        ]
        
        # 尝试不同字体，使用指定大小
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, target_size)
                    # 测试字体是否可用
                    test_img = Image.new('RGB', (100, 100), 'white')
                    test_draw = ImageDraw.Draw(test_img)
                    test_draw.text((10, 10), 'A', font=font, fill='black')
                    return font
                except Exception as e:
                    continue
        
        # 如果都失败了，返回None使用默认处理
        return None
    except Exception as e:
        return None


def generate_captcha_image(text, width=200, height=80):
    """
    生成验证码图片 - 超大字体版本
    增加画布尺寸，使用更大字体确保字符清晰可见
    """
    # 创建更大的画布，浅灰色背景
    image = Image.new('RGB', (width, height), color=(248, 248, 248))
    draw = ImageDraw.Draw(image)
    
    # 添加很少的背景噪点
    for _ in range(15):
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        color = (random.randint(220, 240), random.randint(220, 240), random.randint(220, 240))
        draw.point((x, y), fill=color)
    
    # 获取字体 - 使用很大的字体尺寸
    font = get_best_font(target_size=52)  # 使用52像素字体
    
    # 计算字符位置
    char_count = len(text)
    char_width = width // char_count
    
    # 定义高对比度颜色
    colors = [
        (220, 20, 60),   # 深红色
        (30, 144, 255),  # 蓝色
        (34, 139, 34),   # 深绿色
        (138, 43, 226),  # 紫色
        (255, 69, 0),    # 橙红色
        (0, 100, 0),     # 深绿色
    ]
    
    # 绘制每个字符
    for i, char in enumerate(text):
        # 计算字符位置 - 居中对齐
        char_x = i * char_width + (char_width - 40) // 2 + random.randint(-3, 3)
        char_y = (height - 52) // 2 + random.randint(-3, 3)  # 垂直居中
        
        # 随机选择颜色
        color = random.choice(colors)
        
        if font is None:
            # 如果没有TrueType字体，使用默认字体多次绘制模拟大字体
            base_x, base_y = char_x, char_y
            # 绘制多层字符增加厚度和大小感
            for layer in range(8):  # 增加层数
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        draw.text((base_x + dx + layer//4, base_y + dy + layer//4), 
                                char, fill=color)
        else:
            # 使用TrueType字体 - 主字符
            draw.text((char_x, char_y), char, fill=color, font=font)
            
            # 添加阴影效果增强视觉效果
            shadow_color = tuple(max(0, c - 40) for c in color)
            draw.text((char_x + 2, char_y + 2), char, fill=shadow_color, font=font)
            
            # 添加轻微描边增强字符边缘
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                edge_color = tuple(min(255, c + 20) for c in color)
                draw.text((char_x + dx, char_y + dy), char, fill=edge_color, font=font)
    
    # 添加很少的干扰线
    for _ in range(2):
        x1, y1 = random.randint(0, width//4), random.randint(0, height)
        x2, y2 = random.randint(3*width//4, width), random.randint(0, height)
        line_color = (random.randint(180, 220), random.randint(180, 220), random.randint(180, 220))
        draw.line([(x1, y1), (x2, y2)], fill=line_color, width=1)
    
    # 转换为base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', quality=95)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generate_captcha():
    """生成验证码（文本和图片）"""
    text = generate_captcha_text()
    image = generate_captcha_image(text)
    return text, image