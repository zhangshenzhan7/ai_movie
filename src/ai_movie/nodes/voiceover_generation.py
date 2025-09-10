import os
from typing import Any

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from openai import OpenAI

from .state import VideoGenerationState

# 音色列表
VOICE_LIST = [
    {"name": "龙楠", "voice": "longnan_v2", "traits": "睿智青年男", "scenarios": "通用", "languages": "中、英"},
    {"name": "龙媛", "voice": "longyuan_v2", "traits": "温暖治愈女", "scenarios": "通用", "languages": "中、英"},
    {"name": "龙安柔", "voice": "longanrou", "traits": "温柔闺蜜女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙嫱", "voice": "longqiang_v2", "traits": "浪漫风情女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙寒", "voice": "longhan_v2", "traits": "温暖痴情男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙星", "voice": "longxing_v2", "traits": "温婉邻家女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙华", "voice": "longhua_v2", "traits": "元气甜美女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙婉", "voice": "longwan_v2", "traits": "积极知性女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙橙", "voice": "longcheng_v2", "traits": "智慧青年男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙菲菲", "voice": "longfeifei_v2", "traits": "甜美娇气女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙小诚", "voice": "longxiaocheng_v2", "traits": "磁性低音男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙哲", "voice": "longzhe_v2", "traits": "呆板大暖男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙颜", "voice": "longyan_v2", "traits": "温暖春风女", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙天", "voice": "longtian_v2", "traits": "磁性理智男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙泽", "voice": "longze_v2", "traits": "温暖元气男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙邵", "voice": "longshao_v2", "traits": "积极向上男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙浩", "voice": "longhao_v2", "traits": "多情忧郁男", "scenarios": "社交陪伴", "languages": "中、英"},
    {"name": "龙深", "voice": "kabuleshen_v2", "traits": "实力歌手男", "scenarios": "歌手", "languages": "中、英"},
    {"name": "龙杰力豆", "voice": "longjielidou_v2", "traits": "阳光顽皮男", "scenarios": "童声", "languages": "中、英"},
    {"name": "龙铃", "voice": "longling_v2", "traits": "稚气呆板女", "scenarios": "童声", "languages": "中、英"},
    {"name": "龙可", "voice": "longke_v2", "traits": "懵懂乖乖女", "scenarios": "童声", "languages": "中、英"}
]


def select_voice_by_text(text: str, dashscope_api_key: str = None) -> str:
    """
    根据文本内容选择最合适的音色
    
    Args:
        text: 需要合成语音的文本内容
        dashscope_api_key: DashScope API密钥
    
    Returns:
        最合适的音色ID
    """
    # 构建音色列表描述
    voice_descriptions = "\n".join([
        f"- {voice['scenarios']}场景 {voice['name']} ({voice['traits']}) - voice参数: {voice['voice']} - 语言支持: {voice['languages']}"
        for voice in VOICE_LIST
    ])
    
    # 构建提示词
    prompt = f"""你是资深语音导演，唯一任务是：根据用户给出的纯文本内容，从下方「音色库」中选出最合适的音色ID，直接返回该ID，不要解释、不要多余字符。

规则：
1. 先判断文本语言（zh/cn/en），再判断场景（新闻/故事/客服/儿童/方言/营销…），最后判断情绪（中性/欢快/悲伤/惊悚…）。
2. 若文本含多语言，以主要语言为准；若场景冲突，以"场景"优先级高于"情绪"。
3. 只能输出一个存在于音色库里的ID，禁止编造。

音色库：
{voice_descriptions}

用户文本内容：
{text}"""

    try:
        # 初始化DashScope客户端
        client = OpenAI(
            api_key=dashscope_api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 调用模型选择音色
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        
        voice_id = completion.choices[0].message.content.strip()
        # 验证返回的音色ID是否在列表中
        for voice in VOICE_LIST:
            if voice["voice"] == voice_id:
                return voice_id
        
        # 如果返回的ID不在列表中，使用默认音色
        return "longhua_v2"
    except Exception as e:
        print(f"Error selecting voice: {e}")
        # 出错时使用默认音色
        return "longhua_v2"


def synthesize_speech_from_text(text: str, file_path: str, voice: str = "longhua_v2"):
    try:
        speech_synthesizer = SpeechSynthesizer(
            model="cosyvoice-v2",
            voice=voice,
            callback=None,
        )
        audio = speech_synthesizer.call(text)
        with open(file_path, "wb") as f:
            f.write(audio)
        print(f"Synthesized text {text} to file : {file_path}")
        print(
            f"[Metric] requestId: {speech_synthesizer.get_last_request_id()}, first package delay ms: {speech_synthesizer.get_first_package_delay()}"
        )
    except Exception as e:
        print(f"Error synthesizing speech: {e}")
        raise e


async def voiceover_generation_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: Voiceover generation node")

    if not dashscope.api_key:
        raise Exception("DASHSCOPE_API_KEY environment variable is not set")

    timestamped_audio_dir = os.path.join(state["root_dir"], "audio_files")
    # 确保音频目录存在
    os.makedirs(timestamped_audio_dir, exist_ok=True)
    audio_files = []

    try:
        # 分析整个故事板的文本，选择最合适的音色
        all_dialogues = " ".join([scene.get("dialogue", "") for scene in state["storyboard"] if scene.get("dialogue")])
        selected_voice = select_voice_by_text(all_dialogues, dashscope.api_key)
        print(f"Selected voice: {selected_voice}")

        for i, scene in enumerate(state["storyboard"]):
            dialogue = scene.get("dialogue", "")

            if dialogue:
                file_name = f"{i}.mp3"
                file_path = os.path.join(timestamped_audio_dir, file_name)
                synthesize_speech_from_text(dialogue, file_path, selected_voice)

                audio_files.append(file_path)
            else:
                print(f"Warning: No dialogue found for scene {i}")

    except Exception as e:
        print(f"Error generating voiceovers: {e}")
        raise Exception(f"Error generating voiceovers: {e}")

    return {"audio_files": audio_files}