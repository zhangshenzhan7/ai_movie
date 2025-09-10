"""
AI电影生成项目统一异常处理模块

定义项目中使用的所有异常类型，提供统一的异常处理机制。
"""

class VideoGenerationException(Exception):
    """视频生成相关异常基类"""
    
    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典格式，便于API返回"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "status": "failed"
        }


class APIException(VideoGenerationException):
    """外部API调用异常"""
    pass


class DashScopeAPIException(APIException):
    """DashScope API调用异常"""
    pass


class VideoProcessingException(VideoGenerationException):
    """视频处理异常"""
    pass


class AudioProcessingException(VideoGenerationException):
    """音频处理异常"""
    pass


class FileProcessingException(VideoGenerationException):
    """文件处理异常"""
    pass


class ConfigurationException(VideoGenerationException):
    """配置错误异常"""
    pass


class ValidationException(VideoGenerationException):
    """输入验证异常"""
    pass


class DatabaseException(VideoGenerationException):
    """数据库操作异常"""
    pass


class OSSException(VideoGenerationException):
    """OSS存储异常"""
    pass


class WorkflowException(VideoGenerationException):
    """工作流执行异常"""
    pass