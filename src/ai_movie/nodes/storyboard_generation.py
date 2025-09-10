import json
import os
from typing import Any

from openai import OpenAI

from .state import VideoGenerationState
from ai_movie.core.exceptions import APIException, DashScopeAPIException
from ai_movie.core.logging_config import workflow_logger
from ai_movie.core.config import config


async def storyboard_generation_node(state: VideoGenerationState) -> dict[str, Any]:
    workflow_logger.log_task_start("storyboard_generation", 
                                  user_id=state.get("user_id"),
                                  video_id=state.get("video_db_id"),
                                  video_topic=state["video_topic"])

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
           你是一位「一镜到底」短视频导演+编剧。  
           请根据主题「{state['video_topic']}」一次性产出：  
           1) 网感标题（≤18字，带悬念或数字）  
           2) 口播文案（≤200字，10-20字短句，节奏感）  
           3) 10 个以内分镜脚本，做到真正“一镜到底”无跳切。

           【强制要求】  
           A. 主题一致性（防跑题）  
              - 主角固定：物种、性别、年龄、服装、关键道具全部锁死，写进<cast>字段。  
              - 场景固定：时间、地点、色调、天气写进<scene>字段。  
              - 情绪曲线：起(勾子)→承(冲突)→转(反转)→合(高潮)→尾(号召)，共 5 句以内。     



           B. 镜头连贯性（防跳切）  
              - 用「镜头运动+动作」方式串场：  
                例：①全景推→②跟拍手部特写→③手持上摇到脸→④环绕产品→⑤拉远收镜。  
              - 每个分镜最后一帧画面＝下一分镜第一帧画面（动作或视线连续）。  
              - 只允许 4 种过渡方式：推、拉、跟、摇。禁止跳切、黑场。  

           C. 可拍性（防拍不出）  
              - 文案里每个意象都能在提示词中找到对应画面。  
              - 提示词必须包含：镜头类型、机位运动、主体动作、场景细节、光影氛围。  
              - 禁止出现“感受、震撼、高级”等抽象词。  

           输出 JSON（严禁多余字段，严禁注释）：
           {{
             "title": "18字以内标题",
             "cast": {{ "物种":"","性别":"","年龄":"","服装":"","道具":"" }},
             "scene": {{ "时间":"","地点":"","色调":"","天气":"" }},
             "mood": ["起","承","转","合","尾"],
             "storyboard":[
                 {{
                   "dialogue":"必须是15字左右的台词，口语",
                   "prompt":"镜头+动作+场景+光影，一行写完"
                 }}
             ]
           }}
           """

        completion = client.chat.completions.create(
            model=config.ai.text_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的视频人员，擅长将文案分解为具体的视频场景。请严格按照要求的JSON格式回复，不要包含其他内容。特别注意要控制每个场景的台词长度在20-30个字符以内。",
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

        storyboard = response_data.get("storyboard", [])

        if not isinstance(storyboard, list):
            workflow_logger.warning("分镜结果不是列表，使用备用方案",
                                   user_id=state.get("user_id"),
                                   video_id=state.get("video_db_id"))
            
            segments = state["copywriting"].split(".")[:5]  # Take first 5 sentences
            storyboard = []
            for i, segment in enumerate(segments):
                if segment.strip():
                    # Truncate dialogue to ~30 characters for 5-second audio
                    truncated_dialogue = segment.strip()
                    if len(truncated_dialogue) > 30:
                        truncated_dialogue = truncated_dialogue[:30] + "..."
                    storyboard.append(
                        {
                            "dialogue": truncated_dialogue,
                            "prompt": f"High-quality video scene {i + 1} related to: {segment.strip()}",
                        }
                    )
        else:
            for scene in storyboard:
                if "dialogue" in scene and len(scene["dialogue"]) > 30:
                    scene["dialogue"] = scene["dialogue"][:30] + "..."
        
        workflow_logger.log_task_end("storyboard_generation", 
                                    success=True,
                                    user_id=state.get("user_id"),
                                    video_id=state.get("video_db_id"),
                                    storyboard_count=len(storyboard))
        
        return {"storyboard": storyboard}

    except json.JSONDecodeError as e:
        workflow_logger.error("JSON解析失败", 
                            user_id=state.get("user_id"),
                            video_id=state.get("video_db_id"),
                            error=str(e))
        raise APIException(
            "API返回数据格式错误",
            error_code="INVALID_API_RESPONSE_FORMAT"
        )
    except Exception as e:
        workflow_logger.log_exception("Error calling Qwen-Plus API", e,
                                    user_id=state.get("user_id"),
                                    video_id=state.get("video_db_id"))
        raise DashScopeAPIException(
            f"Qwen-Plus API调用失败: {str(e)}",
            error_code="QWEN_API_CALL_FAILED"
        )
