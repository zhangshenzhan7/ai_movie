import os
from typing import Any

from .state import VideoGenerationState


async def bgm_addition_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: BGM addition node")

    bgm_video = os.path.join(
        state["root_dir"], "video_files", f"{len(state['video_segments'])}.mp4"
    )

    return {"final_video": bgm_video}
