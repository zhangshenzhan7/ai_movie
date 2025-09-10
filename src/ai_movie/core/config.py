"""
AI电影生成项目统一配置管理模块

统一管理所有项目配置，包括API密钥、数据库配置、OSS配置等。
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .exceptions import ConfigurationException

# 加载环境变量
load_dotenv()


@dataclass
class DatabaseConfig:
    """数据库配置"""
    use_database: bool = field(default_factory=lambda: os.getenv('USE_DATABASE', 'False').lower() == 'true')
    uri: str = field(default_factory=lambda: os.getenv('SQLALCHEMY_DATABASE_URI', 'mysql+pymysql://root:password@localhost:3306/ai_movie'))
    track_modifications: bool = field(default_factory=lambda: os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true')
    engine_options: Dict[str, Any] = field(default_factory=lambda: {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '300')),
        'pool_pre_ping': True,
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20'))
    })


@dataclass
class OSSConfig:
    """OSS存储配置"""
    access_key_id: Optional[str] = field(default_factory=lambda: os.getenv('OSS_ACCESS_KEY_ID'))
    access_key_secret: Optional[str] = field(default_factory=lambda: os.getenv('OSS_ACCESS_KEY_SECRET'))
    endpoint: Optional[str] = field(default_factory=lambda: os.getenv('OSS_ENDPOINT'))
    bucket: Optional[str] = field(default_factory=lambda: os.getenv('OSS_BUCKET'))
    prefix: str = field(default_factory=lambda: os.getenv('OSS_PREFIX', 'videos'))
    
    def validate(self) -> bool:
        """验证OSS配置是否完整"""
        required_fields = ['access_key_id', 'access_key_secret', 'endpoint', 'bucket']
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        
        if missing_fields:
            raise ConfigurationException(
                f"缺少OSS配置项: {', '.join(missing_fields)}",
                error_code="OSS_CONFIG_MISSING",
                details={'missing_fields': missing_fields}
            )
        return True
    
    def to_dict(self) -> Dict[str, str | None]:
        """转换为字典格式"""
        return {
            'access_key_id': self.access_key_id,
            'access_key_secret': self.access_key_secret,
            'endpoint': self.endpoint,
            'bucket': self.bucket,
            'prefix': self.prefix
        }


@dataclass
class AIConfig:
    """AI服务配置"""
    dashscope_api_key: Optional[str] = field(default_factory=lambda: os.getenv('DASHSCOPE_API_KEY'))
    dashscope_base_url: str = field(default_factory=lambda: os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'))
    
    # 模型配置
    text_model: str = field(default_factory=lambda: os.getenv('TEXT_MODEL', 'qwen-plus'))
    video_model_t2v: str = field(default_factory=lambda: os.getenv('VIDEO_MODEL_T2V', 'wan2.2-t2v-plus'))
    video_model_i2v: str = field(default_factory=lambda: os.getenv('VIDEO_MODEL_I2V', 'wan2.2-i2v-flash'))
    voice_model: str = field(default_factory=lambda: os.getenv('VOICE_MODEL', 'cosyvoice-v1'))
    image_edit_model: str = field(default_factory=lambda: os.getenv('IMAGE_EDIT_MODEL', 'qwen-image-edit'))
    
    # API调用配置
    api_timeout: int = field(default_factory=lambda: int(os.getenv('API_TIMEOUT', '120')))
    api_retry_count: int = field(default_factory=lambda: int(os.getenv('API_RETRY_COUNT', '3')))
    api_retry_delay: int = field(default_factory=lambda: int(os.getenv('API_RETRY_DELAY', '5')))
    
    def validate(self) -> bool:
        """验证AI配置是否完整"""
        if not self.dashscope_api_key:
            raise ConfigurationException(
                "缺少DashScope API密钥",
                error_code="DASHSCOPE_API_KEY_MISSING",
                details={'env_var': 'DASHSCOPE_API_KEY'}
            )
        return True


@dataclass
class FlaskConfig:
    """Flask应用配置"""
    secret_key: str = field(default_factory=lambda: os.getenv('SECRET_KEY', 'your-secret-key-here'))
    host: str = field(default_factory=lambda: os.getenv('FLASK_HOST', '0.0.0.0'))
    port: int = field(default_factory=lambda: int(os.getenv('FLASK_PORT', '5002')))
    debug: bool = field(default_factory=lambda: os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
    threaded: bool = field(default_factory=lambda: os.getenv('FLASK_THREADED', 'True').lower() == 'true')


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    format: str = field(default_factory=lambda: os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_path: Optional[str] = field(default_factory=lambda: os.getenv('LOG_FILE_PATH'))
    max_file_size: int = field(default_factory=lambda: int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')))  # 10MB
    backup_count: int = field(default_factory=lambda: int(os.getenv('LOG_BACKUP_COUNT', '5')))
    
    # 结构化日志配置
    structured_logging: bool = field(default_factory=lambda: os.getenv('STRUCTURED_LOGGING', 'True').lower() == 'true')
    json_format: bool = field(default_factory=lambda: os.getenv('JSON_LOG_FORMAT', 'True').lower() == 'true')


class Config:
    """统一配置管理类"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.oss = OSSConfig()
        self.ai = AIConfig()
        self.flask = FlaskConfig()
        self.logging = LoggingConfig()
    
    def validate_all(self) -> bool:
        """验证所有配置"""
        try:
            self.ai.validate()
            # OSS配置可选，只在需要时验证
            return True
        except ConfigurationException:
            raise
        except Exception as e:
            raise ConfigurationException(
                f"配置验证失败: {str(e)}",
                error_code="CONFIG_VALIDATION_ERROR"
            )
    
    def get_flask_config(self) -> Dict[str, Any]:
        """获取Flask应用配置字典"""
        config_dict = {
            'SECRET_KEY': self.flask.secret_key,
            'USE_DATABASE': self.database.use_database,
            
            # OSS配置
            'OSS_ACCESS_KEY_ID': self.oss.access_key_id,
            'OSS_ACCESS_KEY_SECRET': self.oss.access_key_secret,
            'OSS_ENDPOINT': self.oss.endpoint,
            'OSS_BUCKET': self.oss.bucket,
            'OSS_PREFIX': self.oss.prefix,
        }
        
        # 只在启用数据库时添加数据库配置
        if self.database.use_database:
            config_dict.update({
                'SQLALCHEMY_DATABASE_URI': self.database.uri,
                'SQLALCHEMY_TRACK_MODIFICATIONS': self.database.track_modifications,
                'SQLALCHEMY_ENGINE_OPTIONS': self.database.engine_options,
            })
        
        return config_dict


# 全局配置实例
config = Config()