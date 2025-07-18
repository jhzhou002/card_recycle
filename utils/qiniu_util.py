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
    
    for image_info in image_data_list:
        try:
            # 瓶盖码存储在qrcode文件夹
            file_name = f"qrcode/{image_info['filename']}"
            
            if QINIU_AVAILABLE:
                q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
                token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
                ret, info = put_data(token, file_name, image_info['data'])
                
                if ret and ret.get('key') == file_name:
                    url = f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
                    urls.append(url)
                else:
                    logger.error(f"瓶盖图片上传失败: {info}")
            else:
                # 备用本地存储
                file_obj = ContentFile(image_info['data'])
                saved_path = default_storage.save(file_name, file_obj)
                url = default_storage.url(saved_path)
                urls.append(url)
                
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
        # 收款码存储在collection_code文件夹
        file_name = f"collection_code/{image_data['filename']}"
        
        if QINIU_AVAILABLE:
            q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
            token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
            ret, info = put_data(token, file_name, image_data['data'])
            
            if ret and ret.get('key') == file_name:
                return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
            else:
                logger.error(f"收款码图片上传失败: {info}")
                return None
        else:
            # 备用本地存储
            file_obj = ContentFile(image_data['data'])
            saved_path = default_storage.save(file_name, file_obj)
            return default_storage.url(saved_path)
            
    except Exception as e:
        logger.error(f"上传收款码图片失败: {str(e)}")
        return None