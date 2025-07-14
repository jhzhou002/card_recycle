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


def generate_captcha_image(text, width=120, height=40):
    """生成验证码图片"""
    # 创建图片
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 添加背景噪点
    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # 添加干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), width=1)
    
    # 绘制文字
    try:
        # 尝试使用系统字体
        font_size = 24
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # 计算文字位置
    text_width = len(text) * 20
    text_height = 24
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # 绘制每个字符，添加随机偏移和颜色
    for i, char in enumerate(text):
        char_x = x + i * 25 + random.randint(-3, 3)
        char_y = y + random.randint(-5, 5)
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((char_x, char_y), char, fill=color, font=font)
    
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