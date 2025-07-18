import io
import base64
from PIL import Image, ImageDraw, ImageFont
import uuid
import os


def add_watermark(image_data, watermark_text, position='bottom_right'):
    """
    为图片添加水印
    
    Args:
        image_data: 图片数据（bytes或file object）
        watermark_text: 水印文字内容
        position: 水印位置 ('bottom_right', 'bottom_left', 'top_right', 'top_left')
    
    Returns:
        处理后的图片数据（bytes）
    """
    try:
        # 打开图片
        if hasattr(image_data, 'read'):
            # 如果是文件对象
            image = Image.open(image_data)
        else:
            # 如果是bytes数据
            image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGBA模式以支持透明度
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 创建一个透明的覆盖层
        txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # 尝试加载字体
        font = None
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/System/Library/Fonts/Arial.ttf',
            'C:/Windows/Fonts/arial.ttf',
        ]
        
        font_size = max(20, min(image.width, image.height) // 20)  # 根据图片大小调整字体
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
        
        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 计算水印位置
        margin = 10
        if position == 'bottom_right':
            x = image.width - text_width - margin
            y = image.height - text_height - margin
        elif position == 'bottom_left':
            x = margin
            y = image.height - text_height - margin
        elif position == 'top_right':
            x = image.width - text_width - margin
            y = margin
        else:  # top_left
            x = margin
            y = margin
        
        # 绘制半透明背景
        bg_padding = 5
        draw.rectangle([
            x - bg_padding, 
            y - bg_padding, 
            x + text_width + bg_padding, 
            y + text_height + bg_padding
        ], fill=(0, 0, 0, 128))
        
        # 绘制白色文字
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 255))
        
        # 合并图层
        watermarked = Image.alpha_composite(image, txt_layer)
        
        # 转换回RGB模式
        if watermarked.mode == 'RGBA':
            background = Image.new('RGB', watermarked.size, (255, 255, 255))
            background.paste(watermarked, mask=watermarked.split()[-1])
            watermarked = background
        
        # 保存到BytesIO
        output = io.BytesIO()
        watermarked.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        print(f"添加水印失败: {e}")
        # 如果添加水印失败，返回原图
        if hasattr(image_data, 'read'):
            image_data.seek(0)
            return image_data.read()
        return image_data


def generate_unique_filename(original_filename, prefix=''):
    """
    生成唯一的文件名
    
    Args:
        original_filename: 原始文件名
        prefix: 文件名前缀
    
    Returns:
        唯一的文件名
    """
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext:
        ext = '.jpg'
    
    unique_id = uuid.uuid4().hex
    if prefix:
        return f"{prefix}_{unique_id}{ext}"
    return f"{unique_id}{ext}"


def process_bottle_cap_images(image_files, user_id):
    """
    处理瓶盖二维码图片，添加用户ID水印
    
    Args:
        image_files: 图片文件列表
        user_id: 用户ID
    
    Returns:
        处理后的图片数据列表
    """
    processed_images = []
    watermark_text = f"用户ID: {user_id}"
    
    for image_file in image_files:
        try:
            # 为每张图片添加水印
            watermarked_data = add_watermark(image_file, watermark_text, 'bottom_right')
            processed_images.append({
                'data': watermarked_data,
                'filename': generate_unique_filename(image_file.name, 'qrcode')
            })
        except Exception as e:
            print(f"处理图片失败: {e}")
            continue
    
    return processed_images


def process_payment_code_image(image_file, user_id):
    """
    处理收款码图片，添加用户ID水印
    
    Args:
        image_file: 收款码图片文件
        user_id: 用户ID
    
    Returns:
        处理后的图片数据
    """
    watermark_text = f"用户ID: {user_id}"
    
    try:
        watermarked_data = add_watermark(image_file, watermark_text, 'top_left')
        return {
            'data': watermarked_data,
            'filename': generate_unique_filename(image_file.name, 'payment')
        }
    except Exception as e:
        print(f"处理收款码图片失败: {e}")
        return None