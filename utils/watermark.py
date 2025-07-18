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
        处理后的图片数据（bytes）或None
    """
    try:
        print(f"开始添加水印: {watermark_text}")
        
        # 打开图片
        if hasattr(image_data, 'read'):
            # 如果是文件对象
            print("使用文件对象打开图片")
            image = Image.open(image_data)
        else:
            # 如果是bytes数据
            print("使用bytes数据打开图片")
            image = Image.open(io.BytesIO(image_data))
        
        print(f"图片尺寸: {image.size}, 模式: {image.mode}")
        
        # 转换为RGBA模式以支持透明度
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
            print("已转换为RGBA模式")
        
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
        print(f"计算字体大小: {font_size}")
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    print(f"成功加载字体: {font_path}")
                    break
                except Exception as font_error:
                    print(f"加载字体失败 {font_path}: {font_error}")
                    continue
        
        if font is None:
            font = ImageFont.load_default()
            print("使用默认字体")
        
        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        print(f"文字尺寸: {text_width}x{text_height}")
        
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
        
        print(f"水印位置: ({x}, {y})")
        
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
        print("绘制水印完成")
        
        # 合并图层
        watermarked = Image.alpha_composite(image, txt_layer)
        
        # 转换回RGB模式
        if watermarked.mode == 'RGBA':
            background = Image.new('RGB', watermarked.size, (255, 255, 255))
            background.paste(watermarked, mask=watermarked.split()[-1])
            watermarked = background
            print("已转换回RGB模式")
        
        # 保存到BytesIO
        output = io.BytesIO()
        watermarked.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        result_data = output.getvalue()
        print(f"水印添加成功，输出数据大小: {len(result_data)} bytes")
        return result_data
        
    except Exception as e:
        print(f"添加水印失败: {e}")
        import traceback
        traceback.print_exc()
        return None


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
    
    print(f"开始处理瓶盖图片，共 {len(image_files)} 张")
    
    for i, image_file in enumerate(image_files):
        print(f"处理第 {i+1} 张图片: {image_file.name}")
        
        try:
            # 重置文件指针到开始位置
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            # 读取原始数据
            raw_data = image_file.read()
            print(f"图片 {i+1} 原始数据大小: {len(raw_data)} bytes")
            
            if not raw_data:
                print(f"图片 {i+1} 数据为空，跳过")
                continue
            
            # 先尝试添加水印
            watermarked_data = None
            try:
                if hasattr(image_file, 'seek'):
                    image_file.seek(0)
                watermarked_data = add_watermark(image_file, watermark_text, 'bottom_right')
                if watermarked_data:
                    print(f"图片 {i+1} 水印添加成功，数据大小: {len(watermarked_data)} bytes")
                else:
                    print(f"图片 {i+1} 水印添加返回空数据")
            except Exception as watermark_error:
                print(f"图片 {i+1} 水印添加失败: {watermark_error}")
            
            # 使用水印图片或原图
            final_data = watermarked_data if watermarked_data else raw_data
            
            if final_data:
                processed_images.append({
                    'data': final_data,
                    'filename': generate_unique_filename(image_file.name, 'qrcode')
                })
                print(f"图片 {i+1} 处理完成，最终数据大小: {len(final_data)} bytes")
            else:
                print(f"图片 {i+1} 最终数据为空，跳过")
                
        except Exception as e:
            print(f"处理图片 {i+1} 时发生异常: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"瓶盖图片处理完成，成功处理 {len(processed_images)} 张")
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
    
    print(f"开始处理收款码图片: {image_file.name}")
    
    try:
        # 重置文件指针到开始位置
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        # 读取原始数据
        raw_data = image_file.read()
        print(f"收款码原始数据大小: {len(raw_data)} bytes")
        
        if not raw_data:
            print("收款码数据为空")
            return None
        
        # 尝试添加水印
        watermarked_data = None
        try:
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            watermarked_data = add_watermark(image_file, watermark_text, 'top_left')
            if watermarked_data:
                print(f"收款码水印添加成功，数据大小: {len(watermarked_data)} bytes")
            else:
                print("收款码水印添加返回空数据")
        except Exception as watermark_error:
            print(f"收款码水印添加失败: {watermark_error}")
        
        # 使用水印图片或原图
        final_data = watermarked_data if watermarked_data else raw_data
        
        if final_data:
            result = {
                'data': final_data,
                'filename': generate_unique_filename(image_file.name, 'payment')
            }
            print(f"收款码处理完成，最终数据大小: {len(final_data)} bytes")
            return result
        else:
            print("收款码最终数据为空")
            return None
            
    except Exception as e:
        print(f"处理收款码时发生异常: {e}")
        import traceback
        traceback.print_exc()
        return None