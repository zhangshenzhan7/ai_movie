import operator
from collections.abc import Sequence
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class VideoGenerationState(TypedDict):
    input_text: str
    character_image_path: str | None
    video_topic: str
    keywords: list[str]
    target_duration: int | None
    title: str
    copywriting: str
    root_dir: str | None
    storyboard: list[dict[str, str]]  # List of {dialogue, prompt}
    audio_files: list[str]
    subtitle_file: str
    video_segments: list[str]
    final_video: str
    quality_analysis: str | dict[str, Any]
    quality_acceptable: bool
    current_step: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    oss_url: str  # 上传到OSS的视频URL
    oss_request_id: str  # OSS上传请求ID
    state_csv_path: str  # 本地状态文件路径
    files_deleted: list[str]  # 删除的文件列表
    dirs_deleted: list[str]  # 删除的目录列表
    cleanup_errors: list[str]  # 清理过程中的错误信息
    
    # 用户信息
    user_id: int              # 关联的用户ID
    username: str | None   # 用户名（可选）
    email: str | None      # 用户邮箱（可选）
    
    # 视频数据库记录信息
    video_db_id: int | None   # 视频数据库记录ID
    video_status: str            # 视频处理状态（pending, completed, failed）
    video_error: str | None   # 错误信息（如果有的话）
    
    # 进度跟踪信息
    parsing_started_at: str | None      # 解析开始时间
    parsing_completed_at: str | None    # 解析完成时间
    parsing_status: str                    # 解析状态
    
    storyboard_started_at: str | None   # 分镜开始时间
    storyboard_completed_at: str | None # 分镜完成时间
    storyboard_status: str                 # 分镜状态
    
    generation_started_at: str | None   # 视频生成开始时间
    generation_completed_at: str | None # 视频生成完成时间
    generation_status: str                 # 视频生成状态
    
    concatenation_started_at: str | None   # 合并开始时间
    concatenation_completed_at: str | None # 合并完成时间
    concatenation_status: str                 # 合并状态
    
    oss_upload_started_at: str | None   # OSS上传开始时间
    oss_upload_completed_at: str | None # OSS上传完成时间
    oss_upload_status: str                 # OSS上传状态