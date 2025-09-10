"""
OSS配置修复工具

确保OSS配置在所有场景下都正确加载和使用。
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from ..core.config import config
from ..core.logging_config import get_logger

logger = get_logger(__name__)


def get_oss_config_safe() -> Dict[str, Any]:
    """
    安全获取OSS配置，确保不会返回占位符
    
    Returns:
        Dict[str, Any]: OSS配置字典
    """
    # 强制重新加载环境变量
    load_dotenv(override=True)
    
    # 直接从环境变量获取配置
    oss_config = {
        'access_key_id': os.getenv('OSS_ACCESS_KEY_ID'),
        'access_key_secret': os.getenv('OSS_ACCESS_KEY_SECRET'),
        'endpoint': os.getenv('OSS_ENDPOINT'),
        'bucket': os.getenv('OSS_BUCKET'),
        'prefix': os.getenv('OSS_PREFIX', 'videos')
    }
    
    # 验证配置不是占位符
    forbidden_values = [
        'your-access-key-id',
        'your-access-key-secret', 
        'your-oss-endpoint',
        'your-bucket-name',
        None,
        ''
    ]
    
    for key, value in oss_config.items():
        if value in forbidden_values:
            error_msg = f"OSS配置错误: {key} 是占位符或空值: {value}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # 验证必需字段
    required_fields = ['access_key_id', 'access_key_secret', 'endpoint', 'bucket']
    for field in required_fields:
        if not oss_config.get(field):
            error_msg = f"OSS配置缺失: {field}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    logger.info(f"OSS配置验证通过: bucket={oss_config['bucket']}, endpoint={oss_config['endpoint']}")
    return oss_config


def validate_oss_endpoint(oss_config: Dict[str, Any]) -> bool:
    """
    验证OSS endpoint配置
    
    Args:
        oss_config: OSS配置字典
        
    Returns:
        bool: 配置是否有效
    """
    bucket = oss_config.get('bucket')
    endpoint = oss_config.get('endpoint')
    
    if not bucket or not endpoint:
        return False
    
    # 检查是否是占位符
    if 'your-bucket-name' in bucket or 'your-oss-endpoint' in endpoint:
        logger.error(f"检测到占位符配置: bucket={bucket}, endpoint={endpoint}")
        return False
    
    # 验证endpoint格式
    if not endpoint.startswith('oss-'):
        logger.warning(f"OSS endpoint格式可能不正确: {endpoint}")
    
    # 构建完整的OSS URL用于验证
    full_endpoint = f"{bucket}.{endpoint}"
    logger.info(f"OSS完整endpoint: {full_endpoint}")
    
    return True


def test_oss_connection_safe(oss_config: Optional[Dict[str, Any]] = None) -> bool:
    """
    安全测试OSS连接
    
    Args:
        oss_config: OSS配置，如果为None则自动获取
        
    Returns:
        bool: 连接是否成功
    """
    try:
        import oss2
        
        if oss_config is None:
            oss_config = get_oss_config_safe()
        
        # 验证配置
        if not validate_oss_endpoint(oss_config):
            return False
        
        # 创建认证和bucket对象
        auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
        bucket = oss2.Bucket(auth, oss_config['endpoint'], oss_config['bucket'])
        
        # 测试连接：获取bucket信息
        try:
            bucket_info = bucket.get_bucket_info()
            logger.info(f"OSS连接成功: {bucket_info.name}")
            return True
        except oss2.exceptions.NoSuchBucket:
            logger.error(f"Bucket不存在: {oss_config['bucket']}")
            return False
        except oss2.exceptions.AccessDenied:
            logger.error("OSS访问被拒绝，请检查访问密钥")
            return False
        except Exception as e:
            logger.error(f"OSS连接失败: {e}")
            return False
            
    except ImportError:
        logger.error("oss2库未安装")
        return False
    except Exception as e:
        logger.error(f"OSS连接测试异常: {e}")
        return False


def upload_to_oss_safe(file_path: str, oss_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    安全的OSS上传函数，确保使用正确的配置
    
    Args:
        file_path: 要上传的文件路径
        oss_config: OSS配置，如果为None则自动获取
        
    Returns:
        Dict[str, Any]: 上传结果
    """
    try:
        import oss2
        import uuid
        
        if oss_config is None:
            oss_config = get_oss_config_safe()
        
        # 验证配置
        if not validate_oss_endpoint(oss_config):
            return {
                "oss_url": None,
                "oss_request_id": None,
                "oss_file_path": None,
                "error": "OSS配置验证失败"
            }
        
        # 验证文件存在
        if not os.path.exists(file_path):
            return {
                "oss_url": None,
                "oss_request_id": None,
                "oss_file_path": None,
                "error": f"文件不存在: {file_path}"
            }
        
        # 创建认证和bucket对象
        auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
        bucket = oss2.Bucket(auth, oss_config['endpoint'], oss_config['bucket'])
        
        # 生成唯一文件名
        file_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
        oss_path = f"{oss_config.get('prefix', 'videos')}/{file_name}"
        
        logger.info(f"开始上传文件到OSS: {file_path} -> {oss_path}")
        
        # 使用断点续传
        result = oss2.resumable_upload(bucket, oss_path, file_path)
        
        # 构建OSS URL
        oss_url = f"https://{oss_config['bucket']}.{oss_config['endpoint']}/{oss_path}"
        
        logger.info(f"OSS上传成功: {oss_url}")
        
        return {
            "oss_url": oss_url,
            "oss_request_id": result.request_id,
            "oss_file_path": oss_path,
            "error": None
        }
        
    except Exception as e:
        error_msg = f"OSS上传失败: {str(e)}"
        logger.error(error_msg)
        
        # 详细的错误信息
        if "Failed to resolve" in str(e) or "nodename nor servname provided" in str(e):
            logger.error("DNS解析失败，检查网络连接和OSS配置")
        elif "403" in str(e) or "Access Denied" in str(e):
            logger.error("访问被拒绝，检查OSS访问密钥和权限")
        elif "404" in str(e) or "NoSuchBucket" in str(e):
            logger.error("Bucket不存在，检查Bucket名称")
        
        return {
            "oss_url": None,
            "oss_request_id": None,
            "oss_file_path": None,
            "error": error_msg
        }


def diagnose_oss_config() -> Dict[str, Any]:
    """
    诊断OSS配置问题
    
    Returns:
        Dict[str, Any]: 诊断结果
    """
    diagnosis = {
        "env_loaded": False,
        "config_valid": False,
        "connection_ok": False,
        "issues": [],
        "recommendations": []
    }
    
    try:
        # 检查环境变量加载
        load_dotenv(override=True)
        diagnosis["env_loaded"] = True
        
        # 检查OSS配置
        oss_config = get_oss_config_safe()
        diagnosis["config_valid"] = True
        
        # 检查连接
        if test_oss_connection_safe(oss_config):
            diagnosis["connection_ok"] = True
        else:
            diagnosis["issues"].append("OSS连接失败")
            diagnosis["recommendations"].append("检查网络连接和OSS配置")
            
    except ValueError as e:
        diagnosis["issues"].append(f"配置错误: {str(e)}")
        diagnosis["recommendations"].append("检查.env文件中的OSS配置项")
    except Exception as e:
        diagnosis["issues"].append(f"未知错误: {str(e)}")
        diagnosis["recommendations"].append("联系技术支持")
    
    return diagnosis


if __name__ == "__main__":
    # 自测试
    print("=== OSS配置诊断 ===")
    result = diagnose_oss_config()
    
    print(f"环境变量加载: {'✅' if result['env_loaded'] else '❌'}")
    print(f"配置验证: {'✅' if result['config_valid'] else '❌'}")
    print(f"连接测试: {'✅' if result['connection_ok'] else '❌'}")
    
    if result['issues']:
        print("\n问题:")
        for issue in result['issues']:
            print(f"  - {issue}")
    
    if result['recommendations']:
        print("\n建议:")
        for rec in result['recommendations']:
            print(f"  - {rec}")