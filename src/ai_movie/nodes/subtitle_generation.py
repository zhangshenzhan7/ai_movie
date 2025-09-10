from typing import Any

from .state import VideoGenerationState


async def subtitle_generation_node(state: VideoGenerationState) -> dict[str, Any]:
    print("Executing: Subtitle generation node")
    subtitle_file = f"subtitles_for_{state['title'].replace(' ', '_')}.srt"

    return {"subtitle_file": subtitle_file}
