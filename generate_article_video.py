#!/usr/bin/env python
"""
Complete example: Generate video from article URL

This script demonstrates end-to-end workflow using the new segment-based
approach with get_segment_visual() from article_video.py (line 219).

Usage:
    python generate_article_video.py

Or customize:
    python generate_article_video.py --url "https://example.com/article" \
                                      --voice "en-US-JennyNeural-Female" \
                                      --aspect portrait
"""
import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.models.schema import VideoAspect
from app.services.article_video import (
    process_article_to_segments_sync,
    reset_image_diversity_tracker
)
from loguru import logger

import subprocess

# Chaining with semicolon (;)
# subprocess.run("playwright install; crawl4ai-setup", shell=True)
subprocess.run("crawl4ai-setup", shell=True)

def generate_article_video(
    article_url: str,
    task_id: str = "article_video",
    voice_name: str = "en-US-JennyNeural-Female",
    voice_rate: float = 1.0,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_source: str = "pexels",
    words_per_second: float = 2.5,
    target_language: Optional[str] = None,
    use_image: List[int] = []
):
    """
    Generate a complete video from an article URL.
    
    Args:
        article_url: URL of the article to convert to video
        task_id: Unique identifier for this generation task
        voice_name: TTS voice to use for narration
        voice_rate: Speech rate (1.0 = normal, 0.5 = half speed, 2.0 = double)
        video_aspect: Aspect ratio (portrait/landscape/square)
        video_source: Source for stock videos (pexels/pixabay)
        words_per_second: Speaking speed for duration estimation
        
    Returns:
        Path to final video file, or None if generation failed
    """
    
    logger.info(f"Starting article video generation for: {article_url}")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Voice: {voice_name} @ {voice_rate}x speed")
    logger.info(f"Aspect: {video_aspect}, Source: {video_source}")
    
    # 1. Parse article to segments
    logger.info("=" * 60)
    logger.info("Step 1/6: Parsing article to segments...")
    logger.info("=" * 60)
    
    try:
        segments, image_links, title = process_article_to_segments_sync(article_url, target_language=target_language)
    except Exception as e:
        logger.error(f"Failed to parse article: {e}")
        return None
    
    logger.success(f"✓ Parsed article with title: '{title}'")
    logger.info(f"  - {len(segments)} script segments")
    logger.info(f"  - {len(image_links)} embedded images")
    
    # Setup task directory
    task_dir = os.path.join(config.app.get("storage_path", "./storage"), task_id)
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"  - Output directory: {task_dir}")
    
    # 2. Generate complete segment videos (visual + audio + subtitle merged)
    logger.info("=" * 60)
    logger.info("Step 2/3: Generating complete segment videos...")
    logger.info("=" * 60)
    
    # Reset image diversity tracker to ensure no duplicates across segments
    reset_image_diversity_tracker()
    
    from app.services.article_video import create_complete_segment_video
    
    final_segment_videos = []
    total_duration = 0.0
    
    for i, segment in enumerate(segments):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Processing Segment {i + 1}/{len(segments)}")
        logger.info(f"{'=' * 60}")
        
        try:
            complete_segment_path = create_complete_segment_video(
                segment=segment,
                segment_index=i,
                task_dir=task_dir,
                voice_name=voice_name,
                voice_rate=voice_rate,
                video_aspect=video_aspect,
                video_source=video_source,
                image_links=image_links,
                allowed_image_indices=use_image
            )
            
            if complete_segment_path and os.path.exists(complete_segment_path):
                final_segment_videos.append(complete_segment_path)
                
                # Get duration from the video file
                from moviepy import VideoFileClip
                clip = VideoFileClip(complete_segment_path)
                segment_duration = clip.duration
                clip.close()
                total_duration += segment_duration
                
                logger.success(f"✓ Segment {i + 1} complete: {segment_duration:.2f}s")
            else:
                logger.error(f"✗ Failed to create segment {i + 1}")
                
        except Exception as e:
            logger.error(f"✗ Error creating segment {i + 1}: {e}")
    
    if not final_segment_videos:
        logger.error("No segment videos generated! Cannot continue.")
        return None
    
    logger.info("\n" + "=" * 60)
    logger.success(f"✓ Generated {len(final_segment_videos)}/{len(segments)} complete segment videos")
    logger.info(f"  Total duration: {total_duration:.2f}s")
    logger.info("=" * 60)
    
    # 3. Concatenate all final segment videos
    logger.info("=" * 60)
    logger.info("Step 3/3: Concatenating final video...")
    logger.info("=" * 60)
    
    # Clean title for filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:50]  # Limit length
    final_video_path = os.path.join(task_dir, f"{safe_title}_final.mp4")
    
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        
        logger.info(f"Loading {len(final_segment_videos)} segment videos...")
        clips = [VideoFileClip(p) for p in final_segment_videos]
        
        logger.info("Concatenating segments...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        logger.info(f"Writing final video: {final_video_path}")
        final_video.write_videofile(
            final_video_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None,
            ffmpeg_params=["-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"]
        )
        
        # Cleanup
        for clip in clips:
            clip.close()
        final_video.close()
        
        if not os.path.exists(final_video_path):
            raise Exception("Final video file not created")
            
        logger.success(f"✓ Final video created: {total_duration:.2f}s")
        logger.info(f"  - File: {os.path.basename(final_video_path)}")
        
    except Exception as e:
        logger.error(f"Failed to concatenate videos: {e}")
        return None
    
    # Summary
    logger.info("=" * 60)
    logger.success("VIDEO GENERATION COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Title: {title}")
    logger.info(f"Duration: {audio_duration:.1f}s")
    logger.info(f"Segments: {len(segment_videos)}/{len(segments)}")
    logger.info(f"Output: {final_video_path}")
    logger.info("=" * 60)
    
    return final_video_path


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate video from article URL using segment-based processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default test URL
  python generate_article_video.py
  
  # Custom article
  python generate_article_video.py --url "https://example.com/article"
  
  # Landscape video for YouTube
  python generate_article_video.py --aspect landscape
  
  # Different voice
  python generate_article_video.py --voice "en-GB-SoniaNeural-Female"
  
  # Faster speech
  python generate_article_video.py --rate 1.3
        """
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="https://zhuanlan.zhihu.com/p/1970939067463104119",
        help="Article URL to convert to video (default: test article)"
    )
    
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="Task ID for output directory (default: auto-generated)"
    )
    
    parser.add_argument(
        "--voice",
        type=str,
        default="en-US-JennyNeural-Female",
        help="TTS voice name (default: en-US-JennyNeural-Female)"
    )
    
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Speech rate multiplier (default: 1.0, range: 0.5-2.0)"
    )
    
    parser.add_argument(
        "--aspect",
        type=str,
        choices=["portrait", "landscape", "square"],
        default="portrait",
        help="Video aspect ratio (default: portrait for social media)"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        choices=["pexels", "pixabay"],
        default="pexels",
        help="Stock video source (default: pexels)"
    )
    
    parser.add_argument(
        "--wps",
        type=float,
        default=2.5,
        help="Words per second for duration estimation (default: 2.5)"
    )
    
    parser.add_argument(
        "--lang",
        type=str,
        default='English',
        help="Target language for translation (e.g., 'English')"
    )

    parser.add_argument(
        "--use-image",
        nargs="*",
        type=int,
        default=[],
        help="List of image indices (0-based) to use from article. Default is empty (use no images)."
    )
    
    args = parser.parse_args()
    
    # Convert aspect string to enum
    aspect_map = {
        "portrait": VideoAspect.portrait,
        "landscape": VideoAspect.landscape,
        "square": VideoAspect.square
    }
    video_aspect = aspect_map[args.aspect]
    
    # Generate task ID if not provided
    if not args.task_id:
        import time
        args.task_id = f"article_video_{int(time.time())}"
    
    # Run generation
    final_video = generate_article_video(
        article_url=args.url,
        task_id=args.task_id,
        voice_name=args.voice,
        voice_rate=args.rate,
        video_aspect=video_aspect,
        video_source=args.source,
        words_per_second=args.wps,
        target_language=args.lang,
        use_image=args.use_image
    )
    
    if final_video:
        print(f"\n{'=' * 60}")
        print(f"✓ SUCCESS! Video saved to:")
        print(f"  {final_video}")
        print(f"{'=' * 60}\n")
        return 0
    else:
        print(f"\n{'=' * 60}")
        print(f"✗ FAILED! Video generation unsuccessful")
        print(f"  Check logs above for details")
        print(f"{'=' * 60}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
