"""
AI电影生成项目统一日志系统模块

提供结构化日志记录功能，统一日志格式和处理机制。
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

from .config import config


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础日志信息
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        extra_data = getattr(record, 'extra_data', None)
        if extra_data:
            log_data.update(extra_data)
        
        # 根据配置选择输出格式
        if config.logging.json_format:
            return json.dumps(log_data, ensure_ascii=False)
        else:
            # 传统格式
            msg = f"[{log_data['timestamp']}] {log_data['level']} - {log_data['logger']} - {log_data['message']}"
            if 'exception' in log_data:
                msg += f"\n{log_data['exception']}"
            return msg


class VideoGenerationLogger:
    """视频生成专用日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 避免重复设置
        if self.logger.handlers:
            return
        
        # 设置日志级别
        self.logger.setLevel(getattr(logging, config.logging.level.upper()))
        
        # 创建格式化器
        if config.logging.structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(config.logging.format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（如果配置了文件路径）
        if config.logging.file_path:
            # 确保日志目录存在
            log_file_path = Path(config.logging.file_path)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用轮转文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=config.logging.max_file_size,
                backupCount=config.logging.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # 防止日志传播到根记录器
        self.logger.propagate = False
    
    def _log_with_context(self, level: int, msg: str, **kwargs):
        """带上下文的日志记录"""
        extra_data = {}
        
        # 提取特殊参数
        user_id = kwargs.pop('user_id', None)
        video_id = kwargs.pop('video_id', None)
        task_id = kwargs.pop('task_id', None)
        duration = kwargs.pop('duration', None)
        error = kwargs.pop('error', None)
        
        # 构建额外数据
        if user_id is not None:
            extra_data['user_id'] = user_id
        if video_id is not None:
            extra_data['video_id'] = video_id
        if task_id is not None:
            extra_data['task_id'] = task_id
        if duration is not None:
            extra_data['duration'] = duration
        if error is not None:
            extra_data['error'] = str(error)
        
        # 添加其他自定义字段
        extra_data.update(kwargs)
        
        # 记录日志
        self.logger.log(level, msg, extra={'extra_data': extra_data})
    
    def debug(self, msg: str, **kwargs):
        """调试日志"""
        self._log_with_context(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """信息日志"""
        self._log_with_context(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """警告日志"""
        self._log_with_context(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """错误日志"""
        self._log_with_context(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """严重错误日志"""
        self._log_with_context(logging.CRITICAL, msg, **kwargs)
    
    def log_request_start(self, endpoint: str, method: str, **kwargs):
        """记录请求开始"""
        self.info(
            f"请求开始: {method} {endpoint}",
            endpoint=endpoint,
            method=method,
            **kwargs
        )
    
    def log_request_end(self, endpoint: str, method: str, status_code: int, duration: float, **kwargs):
        """记录请求结束"""
        self.info(
            f"请求结束: {method} {endpoint} - {status_code}",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration=duration,
            **kwargs
        )
    
    def log_task_start(self, task_name: str, **kwargs):
        """记录任务开始"""
        self.info(
            f"任务开始: {task_name}",
            task_name=task_name,
            **kwargs
        )
    
    def log_task_end(self, task_name: str, success: bool, duration: float | None = None, **kwargs):
        """记录任务结束"""
        status = "成功" if success else "失败"
        self.info(
            f"任务结束: {task_name} - {status}",
            task_name=task_name,
            success=success,
            duration=duration,
            **kwargs
        )
    
    def log_api_call(self, api_name: str, success: bool, duration: float | None = None, **kwargs):
        """记录API调用"""
        status = "成功" if success else "失败"
        level = logging.INFO if success else logging.ERROR
        self._log_with_context(
            level,
            f"API调用: {api_name} - {status}",
            api_name=api_name,
            success=success,
            duration=duration,
            **kwargs
        )
    
    def log_exception(self, msg: str, exc: Exception, **kwargs):
        """记录异常信息"""
        self.error(
            msg,
            error=exc,
            exception_type=type(exc).__name__,
            **kwargs
        )


# 预定义的日志记录器
def get_logger(name: str) -> VideoGenerationLogger:
    """获取日志记录器"""
    return VideoGenerationLogger(name)


# 常用日志记录器
app_logger = get_logger('ai_movie.app')
workflow_logger = get_logger('ai_movie.workflow')
api_logger = get_logger('ai_movie.api')
db_logger = get_logger('ai_movie.database')
video_logger = get_logger('ai_movie.video_processing')
audio_logger = get_logger('ai_movie.audio_processing')


def setup_logging():
    """设置全局日志配置"""
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app_logger.info("日志系统初始化完成", log_level=config.logging.level)