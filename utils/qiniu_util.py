try:
    from qiniu import Auth, put_file, put_data, etag
    import qiniu.config
    QINIU_AVAILABLE = True
except ImportError:
    QINIU_AVAILABLE = False

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os
import base64
import logging

logger = logging.getLogger(__name__)


def generate_qiniu_token():
    """生成上传凭证"""
    if not QINIU_AVAILABLE:
        return None
    
    try:
        q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        return q.upload_token(settings.QINIU_BUCKET_NAME, expires=3600)
    except Exception as e:
        logger.error(f"生成七牛云token失败: {str(e)}")
        return None


def upload_to_qiniu(file_path, file_name=None):
    """上传文件到七牛云"""
    if not QINIU_AVAILABLE:
        return upload_to_local(file_path, file_name)
    
    try:
        if not file_name:
            ext = os.path.splitext(file_path)[1]
            file_name = f"card_recycle/{uuid.uuid4().hex}{ext}"
        
        q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
        
        ret, info = put_file(token, file_name, file_path)
        
        if ret and ret.get('key') == file_name:
            return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
        else:
            logger.error(f"七牛云上传失败: {info}")
            return upload_to_local(file_path, file_name)
    except Exception as e:
        logger.error(f"上传到七牛云失败: {str(e)}")
        return upload_to_local(file_path, file_name)


def upload_data_to_qiniu(data, file_name=None):
    """上传数据到七牛云"""
    if not QINIU_AVAILABLE:
        return upload_data_to_local(data, file_name)
    
    try:
        if not file_name:
            file_name = f"card_recycle/{uuid.uuid4().hex}.jpg"
        
        q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
        token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
        
        ret, info = put_data(token, file_name, data)
        
        if ret and ret.get('key') == file_name:
            return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
        else:
            logger.error(f"七牛云数据上传失败: {info}")
            return upload_data_to_local(data, file_name)
    except Exception as e:
        logger.error(f"上传数据到七牛云失败: {str(e)}")
        return upload_data_to_local(data, file_name)


def upload_to_local(file_path, file_name=None):
    """备用：上传到本地存储"""
    try:
        if not file_name:
            ext = os.path.splitext(file_path)[1]
            file_name = f"card_recycle/{uuid.uuid4().hex}{ext}"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        file_obj = ContentFile(content)
        saved_path = default_storage.save(file_name, file_obj)
        return default_storage.url(saved_path)
    except Exception as e:
        logger.error(f"本地存储上传失败: {str(e)}")
        return None


def upload_data_to_local(data, file_name=None):
    """备用：上传数据到本地存储"""
    try:
        if not file_name:
            file_name = f"card_recycle/{uuid.uuid4().hex}.jpg"
        
        file_obj = ContentFile(data)
        saved_path = default_storage.save(file_name, file_obj)
        return default_storage.url(saved_path)
    except Exception as e:
        logger.error(f"本地存储数据上传失败: {str(e)}")
        return None


def upload_bottle_cap_images(image_data_list):
    """
    批量上传瓶盖二维码图片到七牛云qrcode文件夹
    
    Args:
        image_data_list: 图片数据列表，每个元素包含 {'data': bytes, 'filename': str}
    
    Returns:
        上传成功的URL列表
    """
    urls = []
    
    if not image_data_list:
        logger.warning("图片数据列表为空")
        return urls
    
    for i, image_info in enumerate(image_data_list):
        print(f"处理上传第 {i+1} 张瓶盖图片")
        try:
            # 检查image_info是否为None或缺少必要字段
            if not image_info or not isinstance(image_info, dict):
                print(f"第 {i+1} 张图片信息无效: {image_info}")
                logger.error(f"无效的图片信息: {image_info}")
                continue
                
            if 'filename' not in image_info or 'data' not in image_info:
                print(f"第 {i+1} 张图片缺少必要字段: {list(image_info.keys())}")
                logger.error(f"图片信息缺少必要字段: {image_info}")
                continue
                
            if not image_info['data']:
                print(f"第 {i+1} 张图片数据为空: {image_info['filename']}")
                logger.error(f"图片数据为空: {image_info['filename']}")
                continue
            
            print(f"第 {i+1} 张图片验证通过，数据大小: {len(image_info['data'])} bytes")
            
            # 瓶盖码存储在qrcode文件夹
            file_name = f"qrcode/{image_info['filename']}"
            
            if QINIU_AVAILABLE:
                q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
                token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
                ret, info = put_data(token, file_name, image_info['data'])
                
                if ret and ret.get('key') == file_name:
                    url = f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
                    urls.append(url)
                    logger.info(f"瓶盖图片上传成功: {file_name}")
                else:
                    logger.error(f"瓶盖图片上传失败: {info}")
            else:
                # 备用本地存储
                file_obj = ContentFile(image_info['data'])
                saved_path = default_storage.save(file_name, file_obj)
                url = default_storage.url(saved_path)
                urls.append(url)
                logger.info(f"瓶盖图片本地存储成功: {file_name}")
                
        except Exception as e:
            logger.error(f"上传瓶盖图片失败: {str(e)}")
            continue
    
    return urls


def upload_payment_code_image(image_data):
    """
    上传收款码图片到七牛云collection_code文件夹
    
    Args:
        image_data: 图片数据字典 {'data': bytes, 'filename': str}
    
    Returns:
        上传成功的URL或None
    """
    try:
        # 检查image_data是否为None或缺少必要字段
        if not image_data or not isinstance(image_data, dict):
            logger.error(f"无效的收款码图片信息: {image_data}")
            return None
            
        if 'filename' not in image_data or 'data' not in image_data:
            logger.error(f"收款码图片信息缺少必要字段: {image_data}")
            return None
            
        if not image_data['data']:
            logger.error(f"收款码图片数据为空: {image_data.get('filename', 'unknown')}")
            return None
        
        # 收款码存储在collection_code文件夹
        file_name = f"collection_code/{image_data['filename']}"
        
        if QINIU_AVAILABLE:
            q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
            token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
            ret, info = put_data(token, file_name, image_data['data'])
            
            if ret and ret.get('key') == file_name:
                logger.info(f"收款码图片上传成功: {file_name}")
                return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
            else:
                logger.error(f"收款码图片上传失败: {info}")
                return None
        else:
            # 备用本地存储
            file_obj = ContentFile(image_data['data'])
            saved_path = default_storage.save(file_name, file_obj)
            logger.info(f"收款码图片本地存储成功: {file_name}")
            return default_storage.url(saved_path)
            
    except Exception as e:
        logger.error(f"上传收款码图片失败: {str(e)}")
        return None