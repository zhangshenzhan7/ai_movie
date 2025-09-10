import base64
import mimetypes
import os
import ssl
from http import HTTPStatus
from typing import Any

import cv2  # 请确保已 pip install opencv-python
from dashscope import MultiModalConversation, VideoSynthesis

from .state import VideoGenerationState
from ai_movie.core.exceptions import APIException, DashScopeAPIException, VideoProcessingException
from ai_movie.core.logging_config import video_logger
from ai_movie.core.config import config

# Image size requirements for DashScope API
MIN_HEIGHT = 512
MAX_HEIGHT = 4096
MIN_WIDTH = 512
MAX_WIDTH = 4096

def encode_file(file_path):
    """Encode file to base64"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError('Unsupported or unrecognized image format')
    with open(file_path, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f'data:{mime_type};base64,{encoded_string}'


def encode_and_resize_file(file_path: str, video_dir: str, filename: str = "resized_image.jpg") -> str | None:
    """
    Encode file to base64 after resizing it to meet API requirements.
    
    Args:
        file_path: Path to the input image file
        video_dir: Directory to save the resized image
        filename: Name for the resized image file
        
    Returns:
        Base64 encoded string of the resized image, or None if failed
    """
    try:
        # Create path for resized image
        resized_image_path = os.path.join(video_dir, filename)
        
        # Resize the image
        if not resize_image_for_api(file_path, resized_image_path):
            print(f"Failed to resize image: {file_path}")
            return None
        
        # Encode the resized image
        mime_type, _ = mimetypes.guess_type(resized_image_path)
        if not mime_type or not mime_type.startswith('image/'):
            print(f'Unsupported or unrecognized image format: {resized_image_path}')
            return None
        
        with open(resized_image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f'data:{mime_type};base64,{encoded_string}'
    except Exception as e:
        print(f"Error encoding and resizing file: {e}")
        return None


def resize_image_for_api(image_path: str, output_path: str) -> bool:
    """
    Resize an image to meet DashScope API requirements.
    Height and width should be between 512 and 4096 pixels.
    
    Args:
        image_path: Path to the input image
        output_path: Path to save the resized image
        
    Returns:
        True if resizing was successful, False otherwise
    """
    try:
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to read image: {image_path}")
            return False
        
        height, width = image.shape[:2]
        print(f"Original image size: {width}x{height}")
        
        # Check if resizing is needed
        if (MIN_HEIGHT <= height <= MAX_HEIGHT and MIN_WIDTH <= width <= MAX_WIDTH and
            height >= MIN_HEIGHT and width >= MIN_WIDTH):
            # Image is already within acceptable range
            # Just copy it to the output path
            cv2.imwrite(output_path, image)
            return True
        
        # Calculate new dimensions
        # We want to maintain aspect ratio
        scale_factor = 1.0
        
        # If image is too small, scale up
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            scale_factor = max(MIN_HEIGHT / height, MIN_WIDTH / width)
        
        # If image is too large, scale down
        elif height > MAX_HEIGHT or width > MAX_WIDTH:
            scale_factor = min(MAX_HEIGHT / height, MAX_WIDTH / width)
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Ensure dimensions are within bounds
        new_width = max(MIN_WIDTH, min(MAX_WIDTH, new_width))
        new_height = max(MIN_HEIGHT, min(MAX_HEIGHT, new_height))
        
        # Ensure dimensions are multiples of 64 (common requirement for AI models)
        new_width = (new_width // 64) * 64
        new_height = (new_height // 64) * 64
        
        # Make sure we don't go below minimum after rounding
        new_width = max(MIN_WIDTH, new_width)
        new_height = max(MIN_HEIGHT, new_height)
        
        print(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        
        # Resize the image
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Save the resized image
        cv2.imwrite(output_path, resized_image)
        print(f"Resized image saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False


def edit_image_with_qwen(prompt: str, base_image_url: str) -> str | None:
    """
    Edit an image using the Qwen DashScope API and return the URL of the edited image.
    
    Args:
        prompt: The prompt for editing the image
        base_image_url: URL of the base image to edit
        
    Returns:
        URL of the edited image if successful, None otherwise
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("DASHSCOPE_API_KEY not found in environment variables")
        return None
    
    messages = [
        {
            "role": "user",
            "content": [
                {"image": base_image_url},
                {"text": prompt}
            ]
        }
    ]
    
    try:
        response = MultiModalConversation.call(
            api_key=api_key,
            model="qwen-image-edit",  # 使用qwen-image-edit模型
            messages=messages,
            result_format='message',
            stream=False,
        )
        
        # 处理响应，检查是否是生成器对象
        if hasattr(response, '__iter__') and not isinstance(response, dict):
            # 如果是生成器，取第一个响应
            response = next(iter(response))
        
        if hasattr(response, 'status_code') and response.status_code == 200:
            print("Image editing task completed successfully")
            # Extract image URL using the known Qwen API response structure
            if (hasattr(response, 'output') and
                hasattr(response.output, 'choices') and
                len(response.output.choices) > 0 and
                hasattr(response.output.choices[0], 'message') and
                hasattr(response.output.choices[0].message, 'content') and
                len(response.output.choices[0].message.content) > 0):
                content = response.output.choices[0].message.content[0]
                if isinstance(content, dict) and 'image' in content:
                    edited_image_url = content['image']
                    return edited_image_url
            print("Failed to extract image URL from Qwen API response")
            return None
        else:
            status_code = getattr(response, 'status_code', 'unknown')
            code = getattr(response, 'code', 'unknown')
            message = getattr(response, 'message', 'unknown')
            print(f"Failed to create image editing task. HTTP返回码：{status_code}")
            print(f"错误码：{code}")
            print(f"错误信息：{message}")
            return None
    except Exception as e:
        print(f"Error creating image editing task: {e}")
        return None




def generate_image_edit_prompt(previous_scene: dict, current_scene: dict) -> str:
    """
    Generate a prompt for editing an image based on the transition between two scenes.
    
    Args:
        previous_scene: The previous scene dictionary with 'dialogue' and 'prompt'
        current_scene: The current scene dictionary with 'dialogue' and 'prompt'
        
    Returns:
        A prompt for editing the image
    """
    previous_prompt = previous_scene.get("prompt", "")
    current_prompt = current_scene.get("prompt", "")
    
    # Create a more descriptive prompt for the image editing API
    edit_prompt = f"Transform the image to transition from the scene described as '{previous_prompt}' to the scene described as '{current_prompt}'. Maintain visual consistency while adapting the content, characters, and setting to match the new scene description."
    return edit_prompt


async def video_generation_node(state: VideoGenerationState) -> dict[str, Any]:
    video_logger.log_task_start("video_generation", 
                               user_id=state.get("user_id"),
                               video_id=state.get("video_db_id"),
                               scene_count=len(state.get("storyboard", [])))

    if state["root_dir"] is None:
        raise ValueError("root_dir cannot be None")
    
    video_dir = os.path.join(state["root_dir"], "video_files")
    os.makedirs(video_dir, exist_ok=True)

    video_segments = []
    previous_image_url = None  # Keep track of the previous scene's image

    try:
        for i, scene in enumerate(state["storyboard"]):
            prompt = scene.get("prompt", "")
            if prompt:
                try:
                    video_logger.info(f"Generating video for scene {i + 1}/{len(state['storyboard'])}: {prompt[:50]}...",
                                     user_id=state.get("user_id"),
                                     video_id=state.get("video_db_id"),
                                     scene_index=i)
                    
                    # For the first scene, use character image if provided and exists
                    # For subsequent scenes, use image editing API
                    if i == 0:
                        # First scene - use user-provided image if available
                        character_image_path = state.get("character_image_path")
                        if character_image_path and isinstance(character_image_path, str) and os.path.exists(character_image_path):
                            print(f"Using character image with image-to-video (wan2.2-i2v-flash) for scene {i + 1}")
                            # Encode and resize the character image
                            img_url = encode_and_resize_file(character_image_path, video_dir, f"resized_character_image_{i}.jpg")
                            if img_url:
                                # Use image-to-video model with character image
                                rsp = VideoSynthesis.call(
                                    model="wan2.2-i2v-flash",
                                    prompt=prompt,
                                    img_url=img_url,
                                    resolution="480P"
                                )
                                # Save the image URL for use in subsequent scenes
                                previous_image_url = img_url
                            else:
                                print(f"Failed to encode and resize character image, falling back to text-to-video for scene {i + 1}")
                                rsp = VideoSynthesis.call(
                                    model="wan2.2-t2v-plus", prompt=prompt, size="832*480"
                                )
                        else:
                            print(f"Using text-to-video (wan2.2-t2v-plus) for scene {i + 1}")
                            rsp = VideoSynthesis.call(
                                model="wan2.2-t2v-plus", prompt=prompt, size="832*480"
                            )
                    else:
                        # Subsequent scenes - use image editing API
                        if previous_image_url:
                            # Generate edit prompt based on scene transition
                            previous_scene = state["storyboard"][i-1]
                            edit_prompt = generate_image_edit_prompt(previous_scene, scene)
                            
                            print(f"Creating image editing task for scene {i + 1}")
                            edited_image_url = edit_image_with_qwen(edit_prompt, previous_image_url)
                            
                            if edited_image_url:
                                print(f"Using edited image with image-to-video (wan2.2-i2v-flash) for scene {i + 1}")
                                # Use image-to-video model with edited image
                                rsp = VideoSynthesis.call(
                                    model="wan2.2-i2v-flash",
                                    prompt=prompt,
                                    img_url=edited_image_url,
                                    resolution="480P"
                                )
                                # Update previous_image_url for next iteration
                                previous_image_url = edited_image_url
                            else:
                                print(f"Failed to create image editing task, falling back to text-to-video for scene {i + 1}")
                                rsp = VideoSynthesis.call(
                                    model="wan2.2-t2v-plus", prompt=prompt, size="832*480"
                                )
                        else:
                            print(f"No previous image available, using text-to-video (wan2.2-t2v-plus) for scene {i + 1}")
                            rsp = VideoSynthesis.call(
                                model="wan2.2-t2v-plus", prompt=prompt, size="832*480"
                            )

                    if rsp.status_code == HTTPStatus.OK:
                        video_url = rsp.output.video_url
                        print(f"Video generated successfully: {video_url}")

                        import urllib.request

                        video_filename = f"{i}.mp4"
                        video_filepath = os.path.join(video_dir, video_filename)

                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE

                        urllib.request.urlretrieve(video_url, video_filepath)
                        print(f"Video downloaded to: {video_filepath}")
                        video_segments.append(video_filepath)
                    else:
                        print(
                            f'Failed to generate video, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}')
                        video_segments.append(None)
                except Exception as e:
                    print(f"Error generating video for scene {i}: {e}")
                    # Add a placeholder for failed video
                    video_segments.append(None)
            else:
                print(f"Warning: No prompt found for scene {i}")
                video_segments.append(None)
    except Exception as e:
        video_logger.log_exception("Video generation failed", e,
                                  user_id=state.get("user_id"),
                                  video_id=state.get("video_db_id"))
        raise

    return {
        "video_segments": video_segments
    }
