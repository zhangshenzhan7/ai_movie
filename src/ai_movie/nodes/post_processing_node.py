import datetime
import os
import shutil
from typing import Any

import pandas as pd

from ..web.models import Video, db
from ..utils.oss import upload_to_oss
from .state import VideoGenerationState



def save_state_to_csv(state: dict[str, Any], file_path: str) -> dict[str, Any]:
    """将状态追加写入CSV文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 如果文件不存在，写入表头
        mode = 'a' if os.path.exists(file_path) else 'w'
        header = not os.path.exists(file_path)
        
        # 将状态转换为DataFrame并追加写入CSV
        df = pd.DataFrame([state])
        df.to_csv(file_path, mode=mode, header=header, index=False)
        
        return {
            "state_csv_path": file_path,
            "csv_save_time": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"CSV save failed: {e}")
        return {
            "state_csv_path": None,
            "error": str(e)
        }


def cleanup_files(root_dir: str, keep_dirs: list = None) -> dict[str, Any]:
    """清理源文件"""
    if keep_dirs is None:
        keep_dirs = ['output']
    
    result = {
        "files_deleted": [],
        "dirs_deleted": [],
        "errors": []
    }
    
    try:
        if not os.path.exists(root_dir):
            result["errors"].append(f"Directory not found: {root_dir}")
            return result

        # 遍历目录树，从下到上删除
        for root, dirs, files in os.walk(root_dir, topdown=False):
            # 删除文件
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                    result["files_deleted"].append(file_path)
                except Exception as e:
                    result["errors"].append(f"File delete failed: {file_path} - {e}")
            
            # 删除空目录
            dir_path = root
            if os.path.basename(dir_path) not in keep_dirs:
                try:
                    # 如果目录非空，shutil.rmtree
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        result["dirs_deleted"].append(dir_path)
                    else:
                        # 非空目录尝试用rmtree删除
                        try:
                            shutil.rmtree(dir_path)
                            result["dirs_deleted"].append(dir_path)
                        except Exception as e:
                            result["errors"].append(f"Dir delete failed (non-empty): {dir_path} - {e}")
                except OSError as e:
                    result["errors"].append(f"Dir delete failed: {dir_path} - {e}")
        
        return result
    except Exception as e:
        result["errors"].append(f"Cleanup failed: {e}")
        return result


def post_processing_node(state: VideoGenerationState) -> dict[str, Any]:
    """后处理节点：上传OSS、保存状态、清理文件"""
    # 记录OSS上传开始时间
    # oss_upload_start_time = datetime.datetime.now().isoformat()
    
    result = dict(state)
    
    # 获取OSS配置
    oss_config = {
        'access_key_id': os.getenv('OSS_ACCESS_KEY_ID'),
        'access_key_secret': os.getenv('OSS_ACCESS_KEY_SECRET'),
        'endpoint': os.getenv('OSS_ENDPOINT', "oss-cn-beijing.aliyuncs.com"),
        'bucket': os.getenv('OSS_BUCKET',"zsz-model-bj")
    }
    
    # 验证OSS配置
    for key, value in oss_config.items():
        if not value:
            error_msg = f"Missing OSS configuration: {key}"
            print(error_msg)
            result.update({
                "oss_url": None,
                "oss_request_id": None,
                "error": error_msg,
                "oss_upload_completed_at": datetime.datetime.now().isoformat(),
                "oss_upload_status": "failed"
            })
            return result
    
    # 上传最终视频
    final_video_path = state.get('final_video', '')
    if final_video_path and os.path.exists(final_video_path):
        oss_result = upload_to_oss(final_video_path, oss_config)
        result.update(oss_result)
        
        # 更新OSS上传状态
        if oss_result.get("oss_url"):
            result.update({
                "oss_upload_completed_at": datetime.datetime.now().isoformat(),
                "oss_upload_status": "completed"
            })
        else:
            result.update({
                "oss_upload_completed_at": datetime.datetime.now().isoformat(),
                "oss_upload_status": "failed"
            })
    else:
        result.update({
            "oss_upload_completed_at": datetime.datetime.now().isoformat(),
            "oss_upload_status": "failed"
        })
    
    # 保存状态到CSV
    csv_path = os.path.join(os.path.dirname(state['root_dir']), "state.csv")
    csv_result = save_state_to_csv(result, csv_path)
    result.update(csv_result)
    
    # 获取用户信息
    user_id = state.get('user_id')
    if not user_id:
        error_msg = "Missing user information in state"
        print(error_msg)
        result.update({
            "error": error_msg
        })
        return result
    
    try:
        # 创建视频数据库记录
        video = Video(
            user_id=user_id,
            video_url=result.get('oss_url'),
            status="completed" if result.get('oss_url') else "failed"
        )
        db.session.add(video)
        db.session.commit()
        
        # 更新状态中的数据库记录信息
        result.update({
            "video_db_id": video.id,
            "video_status": video.status
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Database operation failed: {e}"
        print(error_msg)
        result.update({
            "error": error_msg,
            "video_status": "failed"
        })
    
    # 清理源文件
    if os.path.exists(state['root_dir']):
       cleanup_files(state['root_dir'])

    # 更新当前步骤
    result["current_step"] = "post_processing"
    
    return result