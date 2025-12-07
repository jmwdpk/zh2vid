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

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.models.schema import VideoAspect
from app.services.article_video import (
    process_article_to_segments_sync,
    get_segment_visual
)
from app.services import voice, subtitle, video
from loguru import logger


def generate_article_video(
    article_url: str,
    task_id: str = "article_video",
    voice_name: str = "en-US-JennyNeural-Female",
    voice_rate: float = 1.0,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_source: str = "pexels",
    words_per_second: float = 2.5
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
        segments, image_links, title = process_article_to_segments_sync(article_url)
    except Exception as e:
        logger.error(f"Failed to parse article: {e}")
        return None
    
    logger.success(f"✓ Parsed article: '{title}'")
    logger.info(f"  - {len(segments)} script segments")
    logger.info(f"  - {len(image_links)} embedded images")
    
    # Setup task directory
    task_dir = os.path.join(config.app.get("storage_path", "./storage"), task_id)
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"  - Output directory: {task_dir}")
    
    # 2. Generate visuals for each segment
    logger.info("=" * 60)
    logger.info("Step 2/6: Generating visuals for segments...")
    logger.info("=" * 60)
    
    segment_videos = []
    
    for i, segment in enumerate(segments, 1):
        # Estimate duration based on text length
        word_count = len(segment.text.split())
        segment_duration = max(3.0, word_count / words_per_second)
        
        logger.info(f"\n[Segment {i}/{len(segments)}]")
        logger.info(f"  Words: {word_count}, Duration: {segment_duration:.1f}s")
        logger.info(f"  Has image: {segment.has_image}, Index: {segment.image_index}")
        logger.info(f"  Text: {segment.text[:80]}...")
        
        try:
            video_path = get_segment_visual(
                segment=segment,
                segment_duration=segment_duration,
                image_links=image_links,
                task_dir=task_dir,
                video_aspect=video_aspect,
                video_source=video_source
            )
            
            if video_path and os.path.exists(video_path):
                segment_videos.append(video_path)
                logger.success(f"  ✓ Generated: {os.path.basename(video_path)}")
            else:
                logger.warning(f"  ✗ Failed to generate visual for segment {i}")
                
        except Exception as e:
            logger.error(f"  ✗ Error generating segment {i}: {e}")
    
    if not segment_videos:
        logger.error("No segment videos generated! Cannot continue.")
        return None
    
    logger.success(f"\n✓ Generated {len(segment_videos)}/{len(segments)} segment videos")
    
    # 3. Generate audio
    logger.info("=" * 60)
    logger.info("Step 3/6: Generating voiceover...")
    logger.info("=" * 60)
    
    full_script = "\n\n".join([seg.text for seg in segments])
    logger.info(f"Script length: {len(full_script)} characters, {len(full_script.split())} words")
    
    try:
        audio_file, audio_duration, sub_maker = voice.create_voiceover(
            text=full_script,
            voice_name=voice_name,
            voice_rate=voice_rate,
            task_id=task_id
        )
    except Exception as e:
        logger.error(f"Failed to generate audio: {e}")
        return None
    
    if not audio_file or not os.path.exists(audio_file):
        logger.error("Audio generation failed!")
        return None
    
    logger.success(f"✓ Generated voiceover: {audio_duration:.1f}s")
    logger.info(f"  - File: {os.path.basename(audio_file)}")
    
    # 4. Generate subtitles
    logger.info("=" * 60)
    logger.info("Step 4/6: Generating subtitles...")
    logger.info("=" * 60)
    
    subtitle_path = None
    try:
        subtitle_path = subtitle.create_subtitle(
            task_id=task_id,
            script=full_script,
            audio_file=audio_file,
            voice_name=voice_name,
            sub_maker=sub_maker
        )
        
        if subtitle_path and os.path.exists(subtitle_path):
            logger.success(f"✓ Generated subtitles: {os.path.basename(subtitle_path)}")
        else:
            logger.warning("Subtitle generation failed, continuing without subtitles")
            
    except Exception as e:
        logger.warning(f"Subtitle generation error (continuing): {e}")
    
    # 5. Combine videos
    logger.info("=" * 60)
    logger.info("Step 5/6: Combining segment videos...")
    logger.info("=" * 60)
    
    combined_video_path = os.path.join(task_dir, "combined_video.mp4")
    
    try:
        video.combine_videos(
            combined_video_path=combined_video_path,
            video_paths=segment_videos,
            audio_file=audio_file,
            video_aspect=video_aspect
        )
        
        if not os.path.exists(combined_video_path):
            raise Exception("Combined video file not created")
            
        logger.success(f"✓ Combined {len(segment_videos)} segments")
        logger.info(f"  - File: {os.path.basename(combined_video_path)}")
        
    except Exception as e:
        logger.error(f"Failed to combine videos: {e}")
        return None
    
    # 6. Add subtitles
    logger.info("=" * 60)
    logger.info("Step 6/6: Finalizing video...")
    logger.info("=" * 60)
    
    # Clean title for filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:50]  # Limit length
    
    if subtitle_path and os.path.exists(subtitle_path):
        final_video_path = os.path.join(task_dir, f"{safe_title}_with_subs.mp4")
        
        try:
            video.add_subtitles(
                video_path=combined_video_path,
                subtitle_path=subtitle_path,
                output_path=final_video_path
            )
            
            if os.path.exists(final_video_path):
                logger.success("✓ Added subtitles to final video")
            else:
                logger.warning("Subtitle burning failed, using video without subtitles")
                final_video_path = combined_video_path
                
        except Exception as e:
            logger.warning(f"Failed to add subtitles (using video without): {e}")
            final_video_path = combined_video_path
    else:
        final_video_path = combined_video_path
        logger.info("No subtitles to add, using combined video as final")
    
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
        words_per_second=args.wps
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
