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
        # 常见字体路径
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',  # macOS
            '/System/Library/Fonts/Arial.ttf',      # macOS
            'C:/Windows/Fonts/arial.ttf',           # Windows
            'C:/Windows/Fonts/calibri.ttf',         # Windows  
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
            '/usr/share/fonts/TTF/arial.ttf',       # Linux
        ]
        
        # 尝试多个字体大小，从大到小
        for font_size in [48, 42, 38, 34, 30]:
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        return ImageFont.truetype(font_path, font_size)
                    except:
                        continue
        
        # 如果都失败了，尝试使用默认字体
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()


def draw_large_character(draw, char, x, y, color, font):
    """绘制一个大字符，使用多重描边增强效果"""
    # 主字符
    draw.text((x, y), char, fill=color, font=font)
    
    # 创建粗体效果 - 多方向描边
    offsets = [
        # 基础8方向
        (-2, -2), (-2, 0), (-2, 2),
        (0, -2),           (0, 2),
        (2, -2),  (2, 0),  (2, 2),
        # 扩展描边
        (-1, -1), (-1, 1), (1, -1), (1, 1),
        (-3, 0), (3, 0), (0, -3), (0, 3)
    ]
    
    # 绘制描边
    for dx, dy in offsets:
        stroke_color = tuple(min(255, max(0, c + 30)) for c in color)
        draw.text((x + dx, y + dy), char, fill=stroke_color, font=font)


def generate_captcha_image(text, width=160, height=60):
    """生成验证码图片 - 重新设计版本"""
    # 创建白色背景图片
    image = Image.new('RGB', (width, height), color=(250, 250, 250))
    draw = ImageDraw.Draw(image)
    
    # 添加淡色背景噪点
    for _ in range(80):
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        color = (random.randint(220, 240), random.randint(220, 240), random.randint(220, 240))
        draw.point((x, y), fill=color)
    
    # 添加淡色干扰线
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        color = (random.randint(180, 200), random.randint(180, 200), random.randint(180, 200))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
    
    # 创建大字体
    font = create_big_font()
    
    # 计算字符位置
    char_count = len(text)
    char_width = width // char_count
    
    # 绘制每个字符
    for i, char in enumerate(text):
        # 计算字符位置
        char_x = i * char_width + char_width // 4 + random.randint(-5, 5)
        char_y = 5 + random.randint(-3, 3)
        
        # 随机字符颜色 - 使用更深的颜色确保可见性
        color = (
            random.randint(20, 80),   # 红色分量
            random.randint(20, 80),   # 绿色分量  
            random.randint(20, 80)    # 蓝色分量
        )
        
        # 绘制大字符
        draw_large_character(draw, char, char_x, char_y, color, font)
    
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