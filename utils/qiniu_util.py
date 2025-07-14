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