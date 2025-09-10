import json
import os
from typing import Any

from openai import OpenAI

from .state import VideoGenerationState
from ai_movie.core.exceptions import APIException, DashScopeAPIException
from ai_movie.core.logging_config import workflow_logger
from ai_movie.core.config import config


async def copywriting_generation_node(state: VideoGenerationState) -> dict[str, Any]:
    workflow_logger.log_task_start("copywriting_generation", 
                                  user_id=state.get("user_id"),
                                  video_id=state.get("video_db_id"),
                                  video_topic=state["video_topic"])

    response_text = None  # 初始化变量
    
    try:
        # 使用配置管理的API密钥和配置
        api_key = os.getenv("DASHSCOPE_API_KEY") or config.ai.dashscope_api_key
        if not api_key:
            raise DashScopeAPIException(
                "DashScope API密钥未配置",
                error_code="DASHSCOPE_API_KEY_MISSING"
            )
        
        client = OpenAI(
            api_key=api_key,
            base_url=config.ai.dashscope_base_url,
        )

        prompt = f"""
        请为以下视频主题创作一个网感标题和一段200字以内的视频文案：
        
        视频主题：{state["video_topic"]}
        
        要求：
        1. 视频是一镜到底的长视频，文案*必须*注意内容的连贯性
        2. 网感标题：要吸引眼球、有话题性、符合当下网络流行趋势
        3. 视频文案：200字以内，内容要生动有趣，适合视频口播，要有节奏感
        
        请严格按照以下JSON格式回复，不要包含其他内容：
        {{
            "title": "吸引眼球的网感标题",
            "copywriting": "200字以内的视频文案"
        }}
        """

        completion = client.chat.completions.create(
            model=config.ai.text_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的短视频文案策划专家，擅长创作网感标题和高质量的视频口播文案，了解当下网络流行趋势。请严格按照要求的JSON格式回复，不要包含其他内容。",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=config.ai.api_timeout,
        )

        response_text = completion.choices[0].message.content
        if not response_text:
            raise APIException(
                "API返回内容为空",
                error_code="EMPTY_API_RESPONSE"
            )
        
        response_data = json.loads(response_text)

        title = response_data.get("title", "")
        copywriting = response_data.get("copywriting", "")

        if not title:
            title = f"爆款标题：{state['video_topic']}"
        if not copywriting:
            copywriting = (
                f"这是关于{state['video_topic']}的精彩内容，绝对让你意想不到！"
            )
        
        workflow_logger.log_task_end("copywriting_generation", 
                                    success=True,
                                    user_id=state.get("user_id"),
                                    video_id=state.get("video_db_id"),
                                    title=title,
                                    copywriting_length=len(copywriting))

        return {"title": title, "copywriting": copywriting}

    except json.JSONDecodeError as e:
        workflow_logger.error("JSON解析失败", 
                            user_id=state.get("user_id"),
                            video_id=state.get("video_db_id"),
                            error=str(e))
        raise APIException(
            "API返回数据格式错误",
            error_code="INVALID_API_RESPONSE_FORMAT",
            details={"raw_response": response_text or "No response received"}
        )
    except Exception as e:
        workflow_logger.log_exception("Error calling Qwen-Plus API", e,
                                    user_id=state.get("user_id"),
                                    video_id=state.get("video_db_id"))
        raise DashScopeAPIException(
            f"Qwen-Plus API调用失败: {str(e)}",
            error_code="QWEN_API_CALL_FAILED"
        )
