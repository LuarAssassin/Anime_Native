# OSS 对象存储路由
from django.urls import path
from animeapi.views.oss_views import FileUploadView, FileBatchUploadView, FileDeleteView, UserFileListView

urlpatterns = [
    # 单文件上传
    path('upload/', FileUploadView.as_view(), name='oss-upload'),
    # 批量文件上传
    path('upload/batch/', FileBatchUploadView.as_view(), name='oss-batch-upload'),
    # 文件删除
    path('delete/', FileDeleteView.as_view(), name='oss-delete'),
    # 用户文件列表（包含所有文件信息和URL）
    path('files/', UserFileListView.as_view(), name='oss-user-files'),
]
