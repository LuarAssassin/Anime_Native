# CloudFlare R2 对象存储微服务
import os
import uuid
import logging
from datetime import datetime
from django.conf import settings
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger('legoapi')


class CloudflareR2Service:
    """Cloudflare R2 对象存储服务 - MVP版本"""
    
    def __init__(self):
        """初始化 R2 客户端"""
        self.config = settings.CLOUDFLARE_R2
        self.bucket_name = self.config['BUCKET_NAME']
        self.public_url = self.config['PUBLIC_URL']
        
        # 初始化 S3 客户端（兼容 R2）
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.config['ENDPOINT'],
            aws_access_key_id=self.config['ACCESS_KEY_ID'],
            aws_secret_access_key=self.config['SECRET_ACCESS_KEY'],
            region_name=self.config['REGION'],
            config=Config(signature_version='s3v4')
        )
        logger.info("CloudflareR2Service 初始化成功")
    
    def upload_file(self, file_obj, project_name, file_type, custom_name=None):
        """
        上传文件到 R2
        
        Args:
            file_obj: 文件对象 (Django UploadedFile)
            project_name: 项目名称 (如 'ai_memo', 'user_avatar')
            file_type: 文件类型 (如 'images', 'documents')
            custom_name: 自定义文件名（可选）
            
        Returns:
            dict: {
                'url': 公共访问URL,
                'file_path': 文件在桶中的路径,
                'file_name': 文件名,
                'original_name': 原始文件名,
                'file_size': 文件大小,
                'content_type': 文件MIME类型
            }
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            short_uuid = str(uuid.uuid4())[:8]
            original_name = custom_name or file_obj.name
            file_name = f"{timestamp}_{short_uuid}_{original_name}"
            
            # 生成文件路径
            file_path = f"{project_name}/{file_type}/{file_name}"
            
            # 上传文件
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                file_path,
                ExtraArgs={
                    'ContentType': file_obj.content_type,
                    'Metadata': {
                        'project': project_name,
                        'type': file_type,
                        'upload_time': timestamp
                    }
                }
            )
            
            # 生成公共URL
            public_url = f"{self.public_url}/{file_path}"
            
            logger.info(f"文件上传成功: {file_path}")
            
            return {
                'url': public_url,
                'file_path': file_path,
                'file_name': file_name,
                'original_name': original_name,
                'file_size': file_obj.size,
                'content_type': file_obj.content_type
            }
            
        except ClientError as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    def delete_file(self, file_path):
        """
        删除文件
        
        Args:
            file_path: 文件在桶中的路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            logger.info(f"文件删除成功: {file_path}")
            return True
        except ClientError as e:
            logger.error(f"文件删除失败: {str(e)}")
            raise Exception(f"文件删除失败: {str(e)}")
    
    def get_file_url(self, file_path):
        """
        获取文件的公共访问URL
        
        Args:
            file_path: 文件在桶中的路径
            
        Returns:
            str: 公共访问URL
        """
        return f"{self.public_url}/{file_path}"


# 创建单例
r2_service = CloudflareR2Service()