import datetime
import os

import dashscope
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from ..nodes.copywriting_generation import copywriting_generation_node
from ..nodes.input_parsing import input_parsing_node
from ..nodes.post_processing_node import post_processing_node
from ..nodes.quality_check import quality_check_node
from ..nodes.state import VideoGenerationState
from ..nodes.storyboard_generation import storyboard_generation_node
from ..nodes.video_concatenation import video_concatenation_node
from ..nodes.video_generation import video_generation_node
from ..nodes.voiceover_generation import voiceover_generation_node

load_dotenv()
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", "")


def create_video_generation_workflow():
    # Initialize the graph
    workflow = StateGraph(VideoGenerationState)

    # Add nodes
    workflow.add_node("input_parsing", input_parsing_node)
    workflow.add_node("copywriting_generation", copywriting_generation_node)
    workflow.add_node("storyboard_generation", storyboard_generation_node)
    workflow.add_node("voiceover_generation", voiceover_generation_node)
    # workflow.add_node("subtitle_generation", subtitle_generation_node)
    workflow.add_node("video_generation", video_generation_node)
    workflow.add_node("video_concatenation", video_concatenation_node)
    # workflow.add_node("bgm_addition", bgm_addition_node)
    workflow.add_node("quality_check", quality_check_node)
    workflow.add_node("post_processing", post_processing_node)
    
    # Add edges
    workflow.add_edge("input_parsing", "copywriting_generation")
    workflow.add_edge("copywriting_generation", "storyboard_generation")
    workflow.add_edge("storyboard_generation", "voiceover_generation")
    workflow.add_edge("voiceover_generation", "video_generation")
    # workflow.add_edge("voiceover_generation", "subtitle_generation")
    # workflow.add_edge("subtitle_generation", "video_generation")
    workflow.add_edge("video_generation", "video_concatenation")
    workflow.add_edge("video_concatenation", "quality_check")
    workflow.add_edge("quality_check", "post_processing")
    workflow.add_edge("post_processing", END)
    # workflow.add_edge("video_concatenation", "bgm_addition")
    # workflow.add_edge("bgm_addition", "quality_check")

    workflow.set_entry_point("input_parsing")

    return workflow.compile()


async def generate_video_from_sentence(input_text: str, character_image_path: str | None = None):
    """Main function to generate a video from a single sentence and optional character image"""
    # Create root timestamp-based directory for this workflow run
    import os

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    root_dir = os.path.join("./output", timestamp)
    os.makedirs(root_dir, exist_ok=True)

    # Create audio and video subdirectories
    audio_dir = os.path.join(root_dir, "audio_files")
    video_dir = os.path.join(root_dir, "video_files")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)

    # Create the workflow
    app = create_video_generation_workflow()

    # Initialize state with progress tracking fields
    initial_state = VideoGenerationState(
        input_text=input_text,
        character_image_path=character_image_path,
        video_topic="",
        keywords=[],
        title="",
        copywriting="",
        storyboard=[],
        audio_files=[],
        subtitle_file="",
        video_segments=[],
        final_video="",
        quality_analysis="",
        quality_acceptable=False,
        current_step="",
        messages=[],
        root_dir=root_dir,
        
        # 初始化进度跟踪字段
        parsing_started_at=None,
        parsing_completed_at=None,
        parsing_status="pending",
        
        storyboard_started_at=None,
        storyboard_completed_at=None,
        storyboard_status="pending",
        
        generation_started_at=None,
        generation_completed_at=None,
        generation_status="pending",
        
        concatenation_started_at=None,
        concatenation_completed_at=None,
        concatenation_status="pending",
        
        oss_upload_started_at=None,
        oss_upload_completed_at=None,
        oss_upload_status="pending",
        
        # 用户信息
        user_id=0,
        username=None,
        email=None,
        
        # 视频数据库记录信息
        video_db_id=None,
        video_status="pending",
        video_error=None,
        
        # 其他字段
        target_duration=None,
        oss_url="",
        oss_request_id="",
        state_csv_path="",
        files_deleted=[],
        dirs_deleted=[],
        cleanup_errors=[],
    )

    final_state = await app.ainvoke(initial_state)
    return final_state