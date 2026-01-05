from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from .utils.models import SoftDeleteModel, SoftDeleteManager, CustomUserManager

# Create your models here.

# 自定义用户表
class CustomUser(AbstractUser, SoftDeleteModel):
    nickname = models.CharField(
        max_length=50, verbose_name="昵称", null=True, blank=True)
    avatar = models.URLField(
        max_length=1000, verbose_name="头像URL", null=True, blank=True)
    gender = models.CharField(
        max_length=1, 
        choices=[
            ('M', '男'),
            ('F', '女'),
            ('O', '其他'),
            ('U', '未知'),
        ], default="U", verbose_name="性别")
    birthday = models.DateField(
        null=True, blank=True, verbose_name="生日")
    age = models.IntegerField(
        null=True, blank=True, verbose_name="年龄")
    company = models.CharField(
        max_length=100, verbose_name="公司", null=True, blank=True)
    position = models.CharField(
        max_length=50, verbose_name="职位", null=True, blank=True)
    phone = models.CharField(
        max_length=15, verbose_name="手机号", null=True, blank=True)
    address = models.CharField(
        max_length=255, verbose_name="地址", null=True, blank=True)

    objects = CustomUserManager()

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username


# 用户对象存储记录
class UserFileRecord(SoftDeleteModel):
    """用户文件上传记录，追踪所有上传到 R2 的文件"""
    
    objects = SoftDeleteManager()
    
    # 用户关联
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='file_records',
        verbose_name="上传用户",
        help_text="上传该文件的用户"
    )
    
    # 文件基本信息
    file_name = models.CharField(
        max_length=500,
        verbose_name="文件名",
        help_text="原始文件名或自定义文件名"
    )
    file_path = models.CharField(
        max_length=1000,
        unique=True,
        verbose_name="文件路径",
        help_text="文件在 R2 中的完整路径"
    )
    file_url = models.URLField(
        max_length=1000,
        verbose_name="访问URL",
        help_text="文件的公共访问地址"
    )
    
    # 文件属性
    file_size = models.BigIntegerField(
        verbose_name="文件大小",
        help_text="文件大小（字节）"
    )
    content_type = models.CharField(
        max_length=200,
        verbose_name="文件类型",
        help_text="MIME 类型，如 image/jpeg"
    )
    
    # 业务分类
    project_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="项目名称",
        help_text="如 ai_memo, user_avatar"
    )
    file_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="文件分类",
        help_text="如 images, documents"
    )
    
    # 额外信息
    description = models.TextField(
        blank=True,
        verbose_name="文件描述",
        help_text="用户自定义的文件描述"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="元数据",
        help_text="其他自定义元数据"
    )
    
    # 访问控制（可选，未来扩展）
    is_public = models.BooleanField(
        default=True,
        verbose_name="是否公开",
        help_text="是否允许公开访问"
    )
    
    # 过期时间（可选，未来扩展）
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="过期时间",
        help_text="文件过期时间，为空则永不过期"
    )
    
    # 时间戳
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="上传时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )
    
    class Meta:
        db_table = "user_file_record"
        verbose_name = "用户文件记录"
        verbose_name_plural = "用户文件记录"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["user", "-uploaded_at"]),
            models.Index(fields=["project_name", "file_type"]),
            models.Index(fields=["user", "project_name"]),
            models.Index(fields=["expires_at"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.file_name}"
    
    @property
    def file_size_mb(self):
        """返回文件大小（MB）"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_expired(self):
        """检查文件是否过期"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at