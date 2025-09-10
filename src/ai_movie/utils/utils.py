import asyncio
import logging
import os
import tempfile
from typing import Any

from dotenv import load_dotenv

from ..nodes.copywriting_generation import (
    copywriting_generation_node,  # 添加copywriting节点
)
from ..nodes.input_parsing import input_parsing_node
from .oss import upload_to_oss

# 导入状态类
from ..nodes.state import VideoGenerationState
from ..nodes.storyboard_generation import storyboard_generation_node
from ..nodes.video_concatenation import video_concatenation_node
from ..nodes.video_generation import video_generation_node
from ..nodes.voiceover_generation import voiceover_generation_node  # 添加音频生成节点


# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_voiceovers(storyboard: list, root_dir: str, dashscope_api_key: str = None) -> list:
    """
    使用voiceover_generation_node生成语音文件
    
    参数:
    storyboard (list): 分镜脚本
    root_dir (str): 根目录路径
    dashscope_api_key (str): DashScope API Key
    
    返回:
    list: 生成的音频文件路径列表
    """
    # 设置DashScope API Key
    if dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
    elif not os.getenv("DASHSCOPE_API_KEY"):
        raise Exception("Missing DashScope API Key")
    
    # 构造状态对象
    state: VideoGenerationState = {
        "storyboard": storyboard,
        "root_dir": root_dir,
        "video_status": "pending"
    }
    
    # 运行异步函数
    result = asyncio.run(voiceover_generation_node(state))
    
    # 返回音频文件路径
    return result.get("audio_files", [])

def parse_user_input(input_text: str, dashscope_api_key: str = None) -> dict[str, Any]:
    """
    使用input_parsing_node解析用户输入的文本内容
    
    参数:
    input_text (str): 用户输入的原始文本
    dashscope_api_key (str): DashScope API Key
    
    返回:
    dict: 解析后的内容结构，包含扩展描述和基本参数
    """
    # 设置DashScope API Key
    if dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
    elif not os.getenv("DASHSCOPE_API_KEY"):
        raise Exception("Missing DashScope API Key")
    
    # 创建初始状态
    state: VideoGenerationState = {
        "input_text": input_text,
        "root_dir": tempfile.gettempdir(),
        "video_status": "pending"
    }
    
    # 运行异步函数
    result = asyncio.run(input_parsing_node(state))
    
    # 转换为期望的格式
    return {
        "original_text": input_text,
        "expanded_description": result.get("video_topic", input_text),
        "video_topic": result.get("video_topic", input_text),  # 添加这一行以确保video_topic字段存在
        "parameters": {
            "duration": result.get("target_duration", 10),
            "style": "default",
            "complexity": "medium"
        }
    }

def generate_copywriting(video_topic: str, dashscope_api_key: str = None) -> dict[str, Any]:
    """
    使用copywriting_generation_node生成视频文案
    
    参数:
    video_topic (str): 视频主题
    dashscope_api_key (str): DashScope API Key
    
    返回:
    dict: 包含标题和文案的字典
    """
    # 设置DashScope API Key
    if dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
    elif not os.getenv("DASHSCOPE_API_KEY"):
        raise Exception("Missing DashScope API Key")
    
    # 构造状态对象
    state: VideoGenerationState = {
        "video_topic": video_topic,
        "root_dir": tempfile.gettempdir(),
        "video_status": "pending"
    }
    
    # 运行异步函数
    result = asyncio.run(copywriting_generation_node(state))
    
    return result

def generate_storyboard(expanded_content: dict[str, Any], dashscope_api_key: str = None) -> list:
    """
    使用storyboard_generation_node根据扩展内容生成分镜脚本
    
    参数:
    expanded_content (dict): 解析后的内容结构
    dashscope_api_key (str): DashScope API Key
    
    返回:
    list: 分镜列表，包含每个场景的详细信息
    """
    # 设置DashScope API Key
    if dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
    elif not os.getenv("DASHSCOPE_API_KEY"):
        raise Exception("Missing DashScope API Key")
    
    # 首先生成视频文案
    copywriting_result = generate_copywriting(expanded_content.get("video_topic", expanded_content.get("expanded_description", "")), dashscope_api_key)
    
    # 构造状态对象，确保包含video_topic字段
    state: VideoGenerationState = {
        "video_topic": expanded_content.get("video_topic", expanded_content.get("expanded_description", "")),
        "copywriting": copywriting_result.get("copywriting", ""),
        "root_dir": tempfile.gettempdir(),
        "video_status": "pending"
    }
    
    # 运行异步函数
    result = asyncio.run(storyboard_generation_node(state))
    
    # 获取原始storyboard数据
    storyboard = result.get("storyboard", [])
    
    # 记录日志以便调试
    logger.info(f"Generated storyboard with {len(storyboard)} scenes")
    for i, scene in enumerate(storyboard):
        logger.info(f"Scene {i}: dialogue='{scene.get('dialogue', '')}', prompt='{scene.get('prompt', '')}'")
    
    return storyboard

def generate_video_scenes(state: dict[str, Any], dashscope_api_key: str = None) -> list:
    """
    使用video_generation_node生成视频场景
    
    参数:
    state (dict): 视频生成状态，包含分镜信息等
    dashscope_api_key (str): DashScope API Key
    
    返回:
    list: 生成的视频片段路径
    """
    # 设置DashScope API Key
    if dashscope_api_key:
        os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key
    elif not os.getenv("DASHSCOPE_API_KEY"):
        raise Exception("Missing DashScope API Key")
    
    # 构造状态对象
    video_state: VideoGenerationState = {
        "storyboard": state.get("storyboard", []),
        "root_dir": state.get("root_dir", tempfile.gettempdir()),
        "video_status": "pending"
    }
    
    # 添加角色图像路径（如果存在）
    if "character_image_path" in state:
        video_state["character_image_path"] = state["character_image_path"]
    
    # 记录日志以便调试
    storyboard = video_state.get("storyboard", [])
    logger.info(f"Video generation state storyboard has {len(storyboard)} scenes")
    for i, scene in enumerate(storyboard):
        logger.info(f"Scene {i}: {scene}")
        if not scene.get("prompt"):
            logger.warning(f"Scene {i} has no prompt: {scene}")
    
    # 运行异步函数
    result = asyncio.run(video_generation_node(video_state))
    
    # 返回视频片段路径
    return result.get("video_segments", [])

def concatenate_videos_with_audio(video_paths: list, audio_paths: list, root_dir: str) -> str:
    """
    使用video_concatenation_node合并视频和音频片段
    
    参数:
    video_paths (list): 视频片段路径列表
    audio_paths (list): 音频片段路径列表
    root_dir (str): 根目录路径
    
    返回:
    str: 合并后的视频路径
    """
    if not video_paths:
        raise Exception("没有视频片段可以合并")
    
    # 构造状态对象
    state: VideoGenerationState = {
        "video_segments": video_paths,
        "audio_files": audio_paths,
        "root_dir": root_dir,
        "video_status": "pending"
    }
    
    # 运行异步函数
    result = asyncio.run(video_concatenation_node(state))
    
    # 返回最终视频路径
    return result.get("final_video", "")

def upload_to_oss_wrapper(final_video_path: str, state: dict[str, Any]) -> dict[str, Any]:
    """
    使用post_processing_node中的upload_to_oss函数上传视频到阿里云OSS
    
    参数:
    final_video_path (str): 最终视频路径
    state (dict): 视频生成状态
    
    返回:
    dict: OSS上传结果，包含oss_url
    """
    if not final_video_path or not os.path.exists(final_video_path):
        raise Exception("视频文件不存在")
    
    # 获取OSS配置
    oss_config = {
        'access_key_id': os.getenv('OSS_ACCESS_KEY_ID'),
        'access_key_secret': os.getenv('OSS_ACCESS_KEY_SECRET'),
        'endpoint': os.getenv('OSS_ENDPOINT'),
        'bucket': os.getenv('OSS_BUCKET'),
        'prefix': os.getenv('OSS_PREFIX', 'videos')
    }
    
    # 验证OSS配置
    for key, value in oss_config.items():
        if not value and key != 'prefix':
            raise Exception(f"缺少OSS配置: {key}")
    
    # 上传文件
    result = upload_to_oss(final_video_path, oss_config)
    
    return result