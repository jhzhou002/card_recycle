import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import base64


def generate_captcha_text(length=4):
    """生成验证码文本"""
    chars = string.ascii_uppercase + string.digits
    # 排除容易混淆的字符
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    return ''.join(random.choice(chars) for _ in range(length))


def generate_captcha_image(text, width=160, height=60):
    """生成验证码图片"""
    # 创建图片
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 添加背景噪点
    for _ in range(150):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))
    
    # 添加干扰线
    for _ in range(4):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 150), random.randint(100, 150), random.randint(100, 150)), width=2)
    
    # 绘制文字
    try:
        # 尝试使用更大的字体
        from PIL import ImageFont
        import os
        
        # 尝试使用系统中的字体文件
        font_paths = [
            '/System/Library/Fonts/Arial.ttf',  # macOS
            '/Windows/Fonts/arial.ttf',         # Windows
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            '/usr/share/fonts/TTF/arial.ttf',   # Linux
        ]
        
        font = None
        font_size = 36  # 增大字体大小
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        # 如果没有找到字体文件，使用默认字体
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # 计算文字位置 - 增大字符宽度以适应更大的字体
    char_width = 35
    total_text_width = len(text) * char_width
    start_x = (width - total_text_width) // 2
    
    # 绘制每个字符，添加随机偏移和颜色
    for i, char in enumerate(text):
        char_x = start_x + i * char_width + random.randint(-3, 3)
        char_y = 8 + random.randint(-5, 5)  # 调整垂直位置以适应更大的字体
        color = (random.randint(0, 60), random.randint(0, 60), random.randint(0, 60))
        
        # 绘制字符主体 - 使用更粗的字体效果
        draw.text((char_x, char_y), char, fill=color, font=font)
        
        # 增强字体粗细效果
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]:
            shadow_x = char_x + dx
            shadow_y = char_y + dy
            if 0 <= shadow_x < width - 30 and 0 <= shadow_y < height - 30:
                shadow_color = tuple(min(255, c + 20) for c in color)
                draw.text((shadow_x, shadow_y), char, fill=shadow_color, font=font)
    
    # 转换为base64字符串
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generate_captcha():
    """生成验证码（文本和图片）"""
    text = generate_captcha_text()
    image = generate_captcha_image(text)
    return text, image