import datetime
import json
import os
from typing import Any

from openai import OpenAI

from .state import VideoGenerationState


async def input_parsing_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: Input parsing node")
    
    # 记录开始时间
    start_time = datetime.datetime.now().isoformat()

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    prompt = f"""
    请将以下用户输入扩展为一个视频主题，并提取3个相关的关键词：
    
    用户输入：{state["input_text"]}
    
    请严格按照以下JSON格式回复，不要包含其他内容：
    {{
        "video_topic": "扩展后的视频主题",
        "keywords": ["关键词1", "关键词2", "关键词3"]
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个视频内容策划专家，擅长将简单的想法扩展为完整的视频主题。请严格按照要求的JSON格式回复，不要包含其他内容。",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        response_text = completion.choices[0].message.content
        response_data = json.loads(response_text)

        video_topic = response_data.get("video_topic", "")
        keywords = response_data.get("keywords", [])

        if not video_topic:
            video_topic = f"Expanded topic based on: {state['input_text']}"
        if not keywords or not isinstance(keywords, list):
            keywords = ["keyword1", "keyword2", "keyword3"]
            
        # 记录完成时间
        end_time = datetime.datetime.now().isoformat()

    except Exception as e:
        print(f"Error calling Qwen-Plus API: {e}")
        # 记录错误完成时间
        end_time = datetime.datetime.now().isoformat()
        raise Exception(f"Error calling Qwen-Plus API: {e}")

    target_duration = state.get("target_duration", 60) or 60  # Default 60 seconds

    return {
        "video_topic": video_topic,
        "keywords": keywords,
        "target_duration": target_duration,
        "parsing_started_at": start_time,
        "parsing_completed_at": end_time,
        "parsing_status": "completed"
    }