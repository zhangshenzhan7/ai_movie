"""
OSS相关工具函数

将OSS上传功能独立出来，避免循环导入问题。
"""
import os
import uuid
from typing import Any

import oss2


def upload_to_oss(file_path: str, oss_config: dict) -> dict[str, Any]:
    """使用断点续传和分片上传OSS"""
    auth = oss2.Auth(oss_config['access_key_id'], oss_config['access_key_secret'])
    bucket = oss2.Bucket(auth, oss_config['endpoint'], oss_config['bucket'])
    
    # 生成唯一文件名
    file_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
    oss_path = f"{oss_config.get('prefix', 'videos')}/{file_name}"
    
    try:
        # 使用断点续传
        rep = oss2.resumable_upload(bucket, oss_path, file_path)
        oss_url = f"https://{oss_config['bucket']}.{oss_config['endpoint']}/{oss_path}"
        return {
            "oss_url": oss_url,
            "oss_request_id": rep.request_id,
            "oss_file_path": oss_path
        }
    except Exception as e:
        print(f"OSS upload failed: {e}")
        return {
            "oss_url": None,
            "oss_request_id": None,
            "oss_file_path": None,
            "error": str(e)
        }