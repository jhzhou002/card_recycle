from qiniu import Auth, put_file, put_data, etag
import qiniu.config
from django.conf import settings
import uuid
import os


def generate_qiniu_token():
    """生成上传凭证"""
    q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    return q.upload_token(settings.QINIU_BUCKET_NAME, expires=3600)


def upload_to_qiniu(file_path, file_name=None):
    """上传文件到七牛云"""
    if not file_name:
        ext = os.path.splitext(file_path)[1]
        file_name = f"card_recycle/{uuid.uuid4().hex}{ext}"
    
    q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
    
    ret, info = put_file(token, file_name, file_path)
    
    if ret and ret.get('key') == file_name:
        return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
    return None


def upload_data_to_qiniu(data, file_name=None):
    """上传数据到七牛云"""
    if not file_name:
        file_name = f"card_recycle/{uuid.uuid4().hex}"
    
    q = Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = q.upload_token(settings.QINIU_BUCKET_NAME, file_name)
    
    ret, info = put_data(token, file_name, data)
    
    if ret and ret.get('key') == file_name:
        return f"{settings.QINIU_BUCKET_DOMAIN}/{file_name}"
    return None