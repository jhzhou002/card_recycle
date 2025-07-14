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
        # 尝试使用系统字体，如果失败则使用默认字体
        font_size = 32
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # 计算文字位置
    char_width = 35  # 每个字符的宽度
    total_text_width = len(text) * char_width
    start_x = (width - total_text_width) // 2
    
    # 绘制每个字符，添加随机偏移和颜色
    for i, char in enumerate(text):
        char_x = start_x + i * char_width + random.randint(-5, 5)
        char_y = 15 + random.randint(-8, 8)  # 垂直居中并添加随机偏移
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
        
        # 绘制字符，字体大小更大
        draw.text((char_x, char_y), char, fill=color, font=font)
        
        # 为每个字符添加一个轻微的旋转效果（通过绘制多次略微偏移的字符来模拟）
        for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            offset_x = char_x + offset[0]
            offset_y = char_y + offset[1]
            if 0 <= offset_x < width - 20 and 0 <= offset_y < height - 20:
                lighter_color = tuple(min(255, c + 50) for c in color)
                draw.text((offset_x, offset_y), char, fill=lighter_color, font=font)
    
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