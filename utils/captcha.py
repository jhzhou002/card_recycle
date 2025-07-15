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


def create_big_font():
    """创建一个大字体对象"""
    try:
        import os
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
        
        # 尝试多个字体大小，从大到小
        for font_size in [36, 32, 28, 24]:
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        return font
                    except Exception as e:
                        continue
        
        # 如果都失败了，使用PIL默认字体并设置合适大小
        try:
            return ImageFont.load_default()
        except:
            # 最后兜底方案
            return None
    except:
        return None


def draw_large_character(draw, char, x, y, color, font):
    """绘制一个大字符，使用多重描边增强效果"""
    if font is None:
        # 使用默认字体绘制大字符
        draw.text((x, y), char, fill=color)
        # 简单描边效果
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), char, fill=color)
    else:
        # 主字符
        draw.text((x, y), char, fill=color, font=font)
        
        # 创建粗体效果 - 简化描边
        offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1),
        ]
        
        # 绘制描边
        for dx, dy in offsets:
            stroke_color = tuple(min(255, max(0, c + 20)) for c in color)
            draw.text((x + dx, y + dy), char, fill=stroke_color, font=font)


def generate_captcha_image(text, width=160, height=60):
    """生成验证码图片 - 简化版本确保可见性"""
    # 创建白色背景图片
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 简化的背景噪点
    for _ in range(20):
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        color = (random.randint(200, 230), random.randint(200, 230), random.randint(200, 230))
        draw.point((x, y), fill=color)
    
    # 创建字体
    font = create_big_font()
    
    # 计算字符位置
    char_count = len(text)
    char_width = width // char_count
    
    # 绘制每个字符
    for i, char in enumerate(text):
        # 计算字符位置 - 更好的居中
        char_x = i * char_width + char_width // 6 + random.randint(-3, 3)
        char_y = 10 + random.randint(-2, 2)
        
        # 使用对比度高的颜色确保可见性
        colors = [
            (255, 0, 0),     # 红色
            (0, 0, 255),     # 蓝色
            (0, 128, 0),     # 绿色
            (128, 0, 128),   # 紫色
            (255, 140, 0),   # 橙色
        ]
        color = random.choice(colors)
        
        # 绘制字符
        if font is None:
            # 使用默认字体，多次绘制增加粗细度
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    draw.text((char_x + dx, char_y + dy), char, fill=color)
        else:
            # 使用TrueType字体
            draw.text((char_x, char_y), char, fill=color, font=font)
            # 添加描边增强效果
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((char_x + dx, char_y + dy), char, fill=color, font=font)
    
    # 转换为base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generate_captcha():
    """生成验证码（文本和图片）"""
    text = generate_captcha_text()
    image = generate_captcha_image(text)
    return text, image