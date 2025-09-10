import os
from typing import Any

from dashscope import MultiModalConversation

from .state import VideoGenerationState


async def quality_check_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: Quality check node")

    final_video_path = state["final_video"]

    if not os.path.exists(final_video_path):
        raise FileNotFoundError(f"Final video file not found: {final_video_path}")

    try:
        video_path = f"file://{final_video_path}"
        messages = [
            {
                "role": "system",
                "content": [
                    {"text": "You are a helpful assistant and a video quality expert."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "video": video_path,
                        "fps": 2,  # Extract 2 frames per second for analysis
                    },
                    {
                        "text": '请分析这段视频的内容质量，包括：1. 镜头切换是否连贯？2. 内容是否合理？3. 整体质量如何？请以JSON格式返回结果，包含"quality_acceptable"字段（布尔值）和"reason"字段（字符串），例如：{"quality_acceptable": true, "reason": "视频质量良好，镜头切换连贯，内容合理。"}'
                    },
                ],
            },
        ]

        response = MultiModalConversation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen-vl-max-latest",
            messages=messages,
        )

        if response and "output" in response and "choices" in response["output"]:
            analysis_text = response["output"]["choices"][0]["message"]["content"][0][
                "text"
            ]
            print(f"Video quality analysis: {analysis_text}")

            try:
                import json

                json_start = analysis_text.find("{")
                json_end = analysis_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = analysis_text[json_start:json_end]
                    analysis_result = json.loads(json_str)
                else:
                    analysis_result = {
                        "quality_acceptable": False,
                        "reason": f"Could not parse JSON from response: {analysis_text}",
                    }
            except json.JSONDecodeError:
                analysis_result = {
                    "quality_acceptable": False,
                    "reason": f"Failed to parse JSON from response: {analysis_text}",
                }
        else:
            print("Failed to get quality analysis from Qwen-VL model")
            analysis_result = {
                "quality_acceptable": False,
                "reason": "Quality analysis not available",
            }

    except Exception as e:
        print(f"Error during quality check: {e}")
        if "SSL" in str(e) or "EOF occurred" in str(e):
            analysis_result = {
                "quality_acceptable": False,
                "reason": "Quality check failed due to SSL/Network issues. This is a common issue and doesn't necessarily mean the video quality is bad.",
            }
        else:
            analysis_result = {
                "quality_acceptable": False,
                "reason": f"Quality check failed: {str(e)}",
            }

    print(f"Quality check completed for {final_video_path}")

    if isinstance(analysis_result, dict):
        quality_acceptable = analysis_result.get("quality_acceptable", False)
    else:
        quality_acceptable = False

    return {
        "final_video": final_video_path,
        "quality_analysis": analysis_result,
        "quality_acceptable": quality_acceptable,
    }
