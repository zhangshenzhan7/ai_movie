#!/usr/bin/env python3
"""
AI Movie Generator - Main Entry Point

Usage:
    python -m ai_movie.cli [options]
    
For web interface:
    python -m ai_movie.web
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加相对导入支持
if __name__ == "__main__":
    # 直接执行时，添加父目录到路径
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai_movie.core.config import Config
    from ai_movie.core.logging_config import get_logger
    from ai_movie.core.video_workflow import generate_video_from_sentence
else:
    # 模块导入时使用相对导入
    from .core.config import Config
    from .core.logging_config import get_logger
    from .core.video_workflow import generate_video_from_sentence

logger = get_logger(__name__)


async def generate_video_cli(input_text: str, character_image: str = None, output_dir: str = None):
    """
    Command line interface for video generation
    
    Args:
        input_text: Text description for video generation
        character_image: Optional path to character image
        output_dir: Output directory for generated video
    """
    try:
        logger.info("Starting video generation", input_text=input_text[:50])
        
        result = await generate_video_from_sentence(
            input_text=input_text,
            character_image_path=character_image
        )
        
        if result and 'final_video' in result:
            logger.info("Video generation completed", 
                       output_path=result['final_video'])
            print(f"✅ Video generated successfully: {result['final_video']}")
            return result['final_video']
        else:
            logger.error("Video generation failed - no output produced")
            print("❌ Video generation failed")
            return None
            
    except Exception as e:
        logger.log_exception("Video generation failed with exception", e)
        print(f"❌ Error: {e}")
        return None


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Movie Generator - Transform text into videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m ai_movie "A cat delivering food in the city"
    python -m ai_movie "Space adventure" --image character.jpg
    python -m ai_movie "Comedy sketch" --output /path/to/output
        """
    )
    
    parser.add_argument(
        "text",
        help="Text description for video generation"
    )
    
    parser.add_argument(
        "--image", "-i",
        help="Path to character image (optional)"
    )
    
    parser.add_argument(
        "--output", "-o", 
        help="Output directory for generated video"
    )
    
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    if args.config:
        Config.load_from_file(args.config)
    
    # Validate input
    if not args.text.strip():
        print("❌ Error: Text description cannot be empty")
        sys.exit(1)
    
    if args.image and not Path(args.image).exists():
        print(f"❌ Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Run video generation
    result = asyncio.run(generate_video_cli(
        input_text=args.text,
        character_image=args.image,
        output_dir=args.output
    ))
    
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()