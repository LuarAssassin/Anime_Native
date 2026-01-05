# OSS 对象存储 API 视图
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from animeapi.services.oss_cloudflare import r2_service
from animeapi.utils.api_response import APIResponse
from django.conf import settings
import logging
import os

logger = logging.getLogger('animeapi')


def validate_file(file_obj):
    """
    验证上传的文件
    
    Args:
        file_obj: Django UploadedFile 对象
    
    Returns:
        tuple: (is_valid, error_message)
    """
    config = settings.FILE_UPLOAD_CONFIG
    
    # 1. 验证文件大小
    if file_obj.size > config['MAX_FILE_SIZE']:
        max_size_mb = config['MAX_FILE_SIZE'] / (1024 * 1024)
        file_size_mb = file_obj.size / (1024 * 1024)
        return False, f'文件 {file_obj.name} 大小 {file_size_mb:.2f}MB 超过限制 {max_size_mb}MB'
    
    # 2. 验证文件类型 (MIME type)
    content_type = file_obj.content_type
    allowed_types = []
    for types in config['ALLOWED_TYPES'].values():
        allowed_types.extend(types)
    
    if content_type not in allowed_types:
        return False, f'文件 {file_obj.name} 类型 {content_type} 不被允许'
    
    # 3. 验证文件扩展名（双重验证）
    file_ext = os.path.splitext(file_obj.name)[1].lower()
    allowed_extensions = []
    for exts in config['ALLOWED_EXTENSIONS'].values():
        allowed_extensions.extend(exts)
    
    if file_ext and file_ext not in allowed_extensions:
        return False, f'文件 {file_obj.name} 扩展名 {file_ext} 不被允许'
    
    return True, None


class FileUploadView(APIView):
    """文件上传接口"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        上传单个文件
        
        请求参数:
            - file: 文件对象 (必填)
            - project_name: 项目名称 (必填，如 'ai_memo', 'user_avatar')
            - file_type: 文件类型 (必填，如 'images', 'documents')
            - custom_name: 自定义文件名 (可选)
            - description: 文件描述 (可选)
        """
        try:
            # 获取参数
            file_obj = request.FILES.get('file')
            project_name = request.data.get('project_name')
            file_type = request.data.get('file_type')
            custom_name = request.data.get('custom_name') or None
            description = request.data.get('description', '')
            
            # 参数验证
            if not file_obj:
                return APIResponse.error(message='缺少文件参数', code=400)
            
            # 检查是否传了多个文件
            if len(request.FILES.getlist('file')) > 1:
                return APIResponse.error(message='单文件上传接口只能上传一个文件，请使用批量上传接口 /upload/batch/', code=400)
            
            if not project_name:
                return APIResponse.error(message='缺少项目名称', code=400)
            if not file_type:
                return APIResponse.error(message='缺少文件类型', code=400)
            
            # 文件验证
            is_valid, error_msg = validate_file(file_obj)
            if not is_valid:
                return APIResponse.error(message=error_msg or '文件验证失败', code=400)
            
            # 1. 上传文件到 R2
            upload_result = r2_service.upload_file(
                file_obj=file_obj,
                project_name=project_name,
                file_type=file_type,
                custom_name=custom_name
            )
            
            # 2. 创建数据库记录
            from animeapi.models import UserFileRecord
            record = UserFileRecord.objects.create(
                user=request.user,
                file_name=upload_result['original_name'],
                file_path=upload_result['file_path'],
                file_url=upload_result['url'],
                file_size=upload_result['file_size'],
                content_type=upload_result['content_type'],
                project_name=project_name,
                file_type=file_type,
                description=description
            )
            
            # 3. 返回结果（包含记录ID）
            result = {
                **upload_result,
                'record_id': record.pk
            }
            
            return APIResponse.success(data=result, message='上传成功')
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            return APIResponse.error(message=f'上传失败: {str(e)}', code=500, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileBatchUploadView(APIView):
    """批量文件上传接口"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        批量上传文件
        
        请求参数:
            - files: 多个文件对象 (必填)
            - project_name: 项目名称 (必填，所有文件共享)
            - file_type: 文件类型 (必填，所有文件共享)
            - description: 文件描述 (可选，所有文件共享)
        """
        try:
            # 获取参数
            files = request.FILES.getlist('files')
            project_name = request.data.get('project_name')
            file_type = request.data.get('file_type')
            description = request.data.get('description', '')
            
            # 调试日志
            logger.info(f"批量上传请求 - FILES: {request.FILES.keys()}, files count: {len(files)}")
            
            # 参数验证
            if not files:
                return APIResponse.error(message='缺少文件参数，请确保字段名为 files（复数）', code=400)
            if not project_name:
                return APIResponse.error(message='缺少项目名称', code=400)
            if not file_type:
                return APIResponse.error(message='缺少文件类型', code=400)
            
            # 批量数量限制验证
            config = settings.FILE_UPLOAD_CONFIG
            if len(files) > config['MAX_BATCH_COUNT']:
                return APIResponse.error(
                    message=f'批量上传文件数量超过限制，最多允许 {config["MAX_BATCH_COUNT"]} 个文件，当前 {len(files)} 个',
                    code=400
                )
            
            logger.info(f"批量上传 - 文件数: {len(files)}, project: {project_name}, type: {file_type}")
            
            # 上传结果
            success_list = []
            failed_list = []
            
            from animeapi.models import UserFileRecord
            
            # 逐个上传
            for file_obj in files:
                try:
                    # 1. 验证文件
                    is_valid, error_msg = validate_file(file_obj)
                    if not is_valid:
                        failed_list.append({
                            'file_name': file_obj.name,
                            'error': error_msg
                        })
                        continue
                    
                    # 2. 上传到 R2
                    upload_result = r2_service.upload_file(
                        file_obj=file_obj,
                        project_name=project_name,
                        file_type=file_type
                    )
                    
                    # 3. 创建数据库记录
                    record = UserFileRecord.objects.create(
                        user=request.user,
                        file_name=upload_result['original_name'],
                        file_path=upload_result['file_path'],
                        file_url=upload_result['url'],
                        file_size=upload_result['file_size'],
                        content_type=upload_result['content_type'],
                        project_name=project_name,
                        file_type=file_type,
                        description=description
                    )
                    
                    success_list.append({
                        **upload_result,
                        'record_id': record.pk
                    })
                    
                except Exception as e:
                    logger.error(f"文件 {file_obj.name} 上传失败: {str(e)}")
                    failed_list.append({
                        'file_name': file_obj.name,
                        'error': str(e)
                    })
            
            # 返回结果
            result = {
                'total': len(files),
                'success_count': len(success_list),
                'failed_count': len(failed_list),
                'success_files': success_list,
                'failed_files': failed_list
            }
            
            if failed_list:
                message = f'部分上传成功：{len(success_list)}/{len(files)}'
            else:
                message = f'全部上传成功：{len(success_list)} 个文件'
            
            return APIResponse.success(data=result, message=message)
            
        except Exception as e:
            logger.error(f"批量上传失败: {str(e)}")
            return APIResponse.error(message=f'批量上传失败: {str(e)}', code=500, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileDeleteView(APIView):
    """文件删除接口"""
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """
        删除文件
        
        请求参数:
            - id: 文件记录ID (必填)
        """
        try:
            from animeapi.models import UserFileRecord
            
            record_id = request.data.get('id')
            
            if not record_id:
                return APIResponse.error(message='缺少文件记录ID', code=400)
            
            # 检查文件记录是否存在且属于当前用户
            record = UserFileRecord.objects.filter(
                id=record_id,
                user=request.user
            ).first()
            
            if not record:
                return APIResponse.error(message='文件不存在或无权限删除', code=404, status_code=status.HTTP_404_NOT_FOUND)
            
            # 1. 删除 R2 上的文件
            r2_service.delete_file(record.file_path)
            
            # 2. 软删除数据库记录（标记删除，不真删）
            record.delete()  # 调用模型实例的 delete()，触发软删除
            
            return APIResponse.success(message='删除成功')
            
        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}")
            return APIResponse.error(message=f'删除失败: {str(e)}', code=500, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserFileListView(APIView):
    """用户文件列表接口"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        获取用户上传的文件列表
        
        查询参数:
            - project_name: 项目名称筛选 (可选)
            - file_type: 文件类型筛选 (可选)
            - page: 页码 (默认1)
            - page_size: 每页数量 (默认20)
        """
        try:
            from animeapi.models import UserFileRecord
            from django.core.paginator import Paginator
            
            # 获取当前用户（已通过认证）
            user = request.user
            
            # 获取查询参数
            project_name = request.query_params.get('project_name')
            file_type = request.query_params.get('file_type')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 构建查询
            queryset = UserFileRecord.objects.filter(user=user)
            
            if project_name:
                queryset = queryset.filter(project_name=project_name)
            if file_type:
                queryset = queryset.filter(file_type=file_type)
            
            # 分页
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 序列化数据
            files = [{
                'id': record.id,
                'file_name': record.file_name,
                'file_path': record.file_path,
                'file_url': record.file_url,
                'file_size': record.file_size,
                'file_size_mb': record.file_size_mb,
                'content_type': record.content_type,
                'project_name': record.project_name,
                'file_type': record.file_type,
                'description': record.description,
                'uploaded_at': record.uploaded_at.isoformat(),
                'is_expired': record.is_expired,
            } for record in page_obj]
            
            return APIResponse.success(data={
                'files': files,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': paginator.count,
                    'total_pages': paginator.num_pages,
                }
            }, message='获取成功')
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return APIResponse.error(message=f'获取失败: {str(e)}', code=500, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

