"""
AI电影生成项目输入验证模块

使用Pydantic进行数据验证，确保输入数据的正确性和完整性。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator, Field
from werkzeug.datastructures import FileStorage

from .exceptions import ValidationException


class VideoGenerationRequest(BaseModel):
    """视频生成请求数据模型"""
    
    input_text: str = Field(..., description="用户输入的文本内容")
    title: str = Field(default="未命名视频", description="视频标题")
    dashscope_api_key: Optional[str] = Field(None, description="DashScope API密钥")
    
    class Config:
        # 允许额外字段
        extra = "forbid"
        # 字段别名
        allow_population_by_field_name = True
    
    @validator('input_text')
    def validate_input_text(cls, v):
        """验证输入文本"""
        if not v or not v.strip():
            raise ValidationException(
                '输入文本不能为空',
                error_code='INPUT_TEXT_EMPTY'
            )
        
        v = v.strip()
        if len(v) < 5:
            raise ValidationException(
                '输入文本至少需要5个字符',
                error_code='INPUT_TEXT_TOO_SHORT',
                details={'min_length': 5, 'current_length': len(v)}
            )
        
        if len(v) > 500:
            raise ValidationException(
                '输入文本不能超过500个字符',
                error_code='INPUT_TEXT_TOO_LONG',
                details={'max_length': 500, 'current_length': len(v)}
            )
        
        return v
    
    @validator('title')
    def validate_title(cls, v):
        """验证标题"""
        if v:
            v = v.strip()
            if len(v) > 100:
                raise ValidationException(
                    '标题不能超过100个字符',
                    error_code='TITLE_TOO_LONG',
                    details={'max_length': 100, 'current_length': len(v)}
                )
        return v or "未命名视频"
    
    @validator('dashscope_api_key')
    def validate_api_key(cls, v):
        """验证API密钥格式"""
        if v and v.strip():
            v = v.strip()
            # 简单的格式验证
            if len(v) < 10:
                raise ValidationException(
                    'API密钥格式不正确',
                    error_code='INVALID_API_KEY_FORMAT'
                )
        return v


class VideoGenerationWithImageRequest(VideoGenerationRequest):
    """带图片的视频生成请求数据模型"""
    
    # 注意：FileStorage 对象无法直接用于 Pydantic 验证
    # 需要在视图层单独处理文件上传
    
    @classmethod
    def from_form_data(cls, form_data: dict, files: dict | None = None):
        """从表单数据创建实例"""
        # 基础数据验证
        base_data = {
            'input_text': form_data.get('input_text', ''),
            'title': form_data.get('title', '未命名视频'),
            'dashscope_api_key': form_data.get('dashscope_api_key')
        }
        
        # 创建基础验证实例
        instance = cls(**base_data)
        
        # 单独验证文件上传
        if files and 'character_image' in files:
            file_obj = files['character_image']
            cls._validate_character_image(file_obj)
        
        return instance
    
    @staticmethod
    def _validate_character_image(file_obj: FileStorage):
        """验证角色图片文件"""
        if not file_obj or not file_obj.filename:
            return  # 文件是可选的
        
        # 检查文件扩展名
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        file_ext = '.' + file_obj.filename.rsplit('.', 1)[-1].lower()
        
        if file_ext not in allowed_extensions:
            raise ValidationException(
                f'不支持的图片格式：{file_ext}',
                error_code='UNSUPPORTED_IMAGE_FORMAT',
                details={
                    'allowed_formats': list(allowed_extensions),
                    'received_format': file_ext
                }
            )
        
        # 检查文件大小（假设最大10MB）
        if hasattr(file_obj, 'content_length') and file_obj.content_length:
            max_size = 10 * 1024 * 1024  # 10MB
            if file_obj.content_length > max_size:
                raise ValidationException(
                    f'图片文件过大，最大支持10MB',
                    error_code='IMAGE_FILE_TOO_LARGE',
                    details={
                        'max_size_mb': 10,
                        'current_size_mb': round(file_obj.content_length / (1024 * 1024), 2)
                    }
                )


class UserRegistrationRequest(BaseModel):
    """用户注册请求数据模型"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, description="密码")
    
    @validator('username')
    def validate_username(cls, v):
        """验证用户名"""
        v = v.strip()
        
        # 检查用户名字符
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValidationException(
                '用户名只能包含字母、数字、下划线和短横线',
                error_code='INVALID_USERNAME_FORMAT'
            )
        
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """验证邮箱格式"""
        import re
        
        v = v.strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, v):
            raise ValidationException(
                '邮箱格式不正确',
                error_code='INVALID_EMAIL_FORMAT'
            )
        
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 6:
            raise ValidationException(
                '密码至少需要6个字符',
                error_code='PASSWORD_TOO_SHORT'
            )
        
        if len(v) > 100:
            raise ValidationException(
                '密码不能超过100个字符',
                error_code='PASSWORD_TOO_LONG'
            )
        
        return v


class UserLoginRequest(BaseModel):
    """用户登录请求数据模型"""
    
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")
    
    @validator('email')
    def validate_email(cls, v):
        """验证邮箱"""
        if not v or not v.strip():
            raise ValidationException(
                '邮箱不能为空',
                error_code='EMAIL_REQUIRED'
            )
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        """验证密码"""
        if not v or not v.strip():
            raise ValidationException(
                '密码不能为空',
                error_code='PASSWORD_REQUIRED'
            )
        return v


class PaginationRequest(BaseModel):
    """分页请求数据模型"""
    
    page: int = Field(default=1, ge=1, description="页码")
    per_page: int = Field(default=10, ge=1, le=100, description="每页数量")
    
    @validator('per_page')
    def validate_per_page(cls, v):
        """验证每页数量"""
        if v > 100:
            raise ValidationException(
                '每页数量不能超过100',
                error_code='PER_PAGE_TOO_LARGE',
                details={'max_per_page': 100}
            )
        return v


def validate_request_data(model_class, data: dict):
    """通用请求数据验证函数"""
    try:
        return model_class(**data)
    except ValueError as e:
        # Pydantic 验证错误
        error_details = []
        if hasattr(e, 'errors'):
            for error in e.errors():
                error_details.append({
                    'field': '.'.join(str(loc) for loc in error['loc']),
                    'message': error['msg'],
                    'type': error['type']
                })
        
        raise ValidationException(
            '输入数据验证失败',
            error_code='VALIDATION_ERROR',
            details={'errors': error_details}
        )
    except ValidationException:
        # 自定义验证异常直接抛出
        raise
    except Exception as e:
        raise ValidationException(
            f'数据验证过程中发生未知错误: {str(e)}',
            error_code='UNKNOWN_VALIDATION_ERROR'
        )