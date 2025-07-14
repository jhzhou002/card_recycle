import os
import uuid
from io import BytesIO
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.deconstruct import deconstructible

try:
    from qiniu import Auth, put_data, BucketManager
    import qiniu.config
    QINIU_AVAILABLE = True
except ImportError:
    QINIU_AVAILABLE = False


@deconstructible
class QiniuStorage(Storage):
    """
    七牛云存储后端
    """
    
    def __init__(self):
        self.access_key = getattr(settings, 'QINIU_ACCESS_KEY', '')
        self.secret_key = getattr(settings, 'QINIU_SECRET_KEY', '')
        self.bucket_name = getattr(settings, 'QINIU_BUCKET_NAME', '')
        self.bucket_domain = getattr(settings, 'QINIU_BUCKET_DOMAIN', '')
        self.secure_url = getattr(settings, 'QINIU_SECURE_URL', True)
        
        if QINIU_AVAILABLE and self.access_key and self.secret_key:
            self.auth = Auth(self.access_key, self.secret_key)
            self.bucket_manager = BucketManager(self.auth)
        else:
            self.auth = None
            self.bucket_manager = None
    
    def _get_key(self, name):
        """生成七牛云存储的key"""
        if name.startswith('card_recycle/'):
            return name
        return f"card_recycle/{name}"
    
    def _save(self, name, content):
        """保存文件到七牛云"""
        if not QINIU_AVAILABLE or not self.auth:
            # 如果七牛云不可用，返回原文件名（会使用本地存储）
            return name
        
        try:
            # 生成唯一的文件名
            ext = os.path.splitext(name)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            key = self._get_key(unique_name)
            
            # 读取文件内容
            content.seek(0)
            data = content.read()
            
            # 生成上传token
            token = self.auth.upload_token(self.bucket_name, key)
            
            # 上传到七牛云
            ret, info = put_data(token, key, data)
            
            if ret and ret.get('key') == key:
                return key
            else:
                # 上传失败，返回原文件名（使用本地存储作为备份）
                return name
                
        except Exception as e:
            # 发生错误时，返回原文件名
            return name
    
    def exists(self, name):
        """检查文件是否存在"""
        if not QINIU_AVAILABLE or not self.bucket_manager:
            return False
        
        try:
            key = self._get_key(name)
            ret, info = self.bucket_manager.stat(self.bucket_name, key)
            return info.status_code == 200
        except:
            return False
    
    def url(self, name):
        """获取文件的访问URL"""
        if not name:
            return ''
        
        # 如果已经是完整URL，直接返回
        if name.startswith('http'):
            return name
        
        # 生成七牛云URL
        key = self._get_key(name)
        if self.bucket_domain:
            protocol = 'https://' if self.secure_url else 'http://'
            return f"{protocol.rstrip('://')}{self.bucket_domain.lstrip('https://').lstrip('http://')}/{key}"
        
        return f"https://{self.bucket_name}.qiniudn.com/{key}"
    
    def size(self, name):
        """获取文件大小"""
        if not QINIU_AVAILABLE or not self.bucket_manager:
            return 0
        
        try:
            key = self._get_key(name)
            ret, info = self.bucket_manager.stat(self.bucket_name, key)
            if info.status_code == 200:
                return ret.get('fsize', 0)
        except:
            pass
        
        return 0
    
    def delete(self, name):
        """删除文件"""
        if not QINIU_AVAILABLE or not self.bucket_manager:
            return False
        
        try:
            key = self._get_key(name)
            ret, info = self.bucket_manager.delete(self.bucket_name, key)
            return info.status_code == 200
        except:
            return False
    
    def listdir(self, path):
        """列出目录内容"""
        # 七牛云不支持传统的目录概念
        return [], []
    
    def get_accessed_time(self, name):
        """获取文件访问时间"""
        return None
    
    def get_created_time(self, name):
        """获取文件创建时间"""
        return None
    
    def get_modified_time(self, name):
        """获取文件修改时间"""
        return None