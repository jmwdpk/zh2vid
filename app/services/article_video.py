"""
Article Video Service
Creates videos from article URLs by parsing content, processing segments,
and generating appropriate visuals for each segment.
"""
import os
import re
import asyncio
import tempfile
from typing import List, Optional, Tuple
from urllib.parse import quote

import requests
from loguru import logger

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect, VideoParams
from app.services.utils.url_parser import parse_url_to_markdown, parse_url_sync
from app.services.utils.process_md import (
    extract_post_info,
    process_markdown,
    get_script_segments,
    ScriptSegment,
)
from app.services import material, video, voice, llm
from app.utils import utils


def translate_text(text: str, target_lang: str = "English") -> str:
    """
    Translate text using pollinations.ai.
    
    Args:
        text: The text to translate
        target_lang: The target language (default: English)
        
    Returns:
        Translated text, or original text if translation fails
    """
    if not text or not text.strip():
        return text
        
    prompt = f"""
# Role: Professional Translator

## Goals:
Translate the following text into {target_lang}.

## Constraints:
1. Maintain the professional and informative tone.
2. Keep the original structure and formatting (markdown).
3. IMPORTANT: Preserve any image patterns like ![]($1$), ![]($2$), etc. EXACTLY as they appear. Do not translate the numbers or symbols within these patterns.
4. Return ONLY the translated text, nothing else.

## Text to Translate:
{text}
""".strip()

    try:
        translated_text = llm.generate_response(prompt, strip_newlines=False)
        
        if translated_text and not translated_text.startswith("Error:"):
            logger.info("Translation successful")
            return translated_text
        
        logger.warning(f"Translation failed or returned error: {translated_text}")
        return text
    except Exception as e:
        logger.error(f"Failed to translate text: {str(e)}")
        return text



def generate_segment_search_terms(segment_text: str, amount: int = 3) -> List[str]:
    """
    Use pollinations.ai to generate search terms for a single script segment.
    
    Args:
        segment_text: The text of the script segment
        amount: Number of search terms to generate (default 3)
        
    Returns:
        List of search terms for finding relevant videos/images
    """
    prompt = f"""
# Role: Video Search Terms Generator

## Goals:
Generate/summarize/extract {amount} search terms for stock videos/images that would visually represent this script segment.

## Constraints:
1. Return ONLY an array of strings, nothing else.
2. Each search term should be 1-3 words.
3. Terms must be in English.
4. Terms should describe visual scenes, objects, or actions that match the text meaning.
5. Focus on concrete, searchable concepts (not abstract ideas).
6. Keep the notable/famous figure's name as a term

## Script Segment:
{segment_text}

## Output Format:
["term1", "term2", "term3"]
""".strip()

    try:
        # Use pollinations.ai API (GET method)
        model_name = config.app.get("pollinations_model_name", "openai-fast")
        url = f"https://text.pollinations.ai/{quote(prompt)}"
        params = {
            "model": model_name,
            "seed": 42
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        content = response.text
        if content:
            # Parse JSON array from response
            import json
            # Find JSON array in response
            match = re.search(r'\[.*?\]', content, re.DOTALL)
            if match:
                search_terms = json.loads(match.group())
                if isinstance(search_terms, list):
                    logger.debug(f"Generated search terms: {search_terms}")
                    return search_terms[:amount]
        
        logger.warning(f"Failed to parse search terms from response: {content}")
        return []
        
    except Exception as e:
        logger.error(f"Failed to generate search terms: {str(e)}")
        return []


def download_image(image_url: str, save_dir: str) -> Optional[str]:
    """
    Download an image from URL and save locally.
    
    Args:
        image_url: URL of the image
        save_dir: Directory to save the image
        
    Returns:
        Local path to saved image, or None if download fails
    """
    try:
        # Generate filename from URL hash
        url_hash = utils.md5(image_url)
        ext = os.path.splitext(image_url.split('?')[0])[-1] or '.jpg'
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            ext = '.jpg'
        
        image_path = os.path.join(save_dir, f"img-{url_hash}{ext}")
        
        # Check if already downloaded
        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            logger.debug(f"Image already exists: {image_path}")
            return image_path
        
        # Download image
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(image_url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        
        os.makedirs(save_dir, exist_ok=True)
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded image: {image_path}")
        return image_path
        
    except Exception as e:
        logger.error(f"Failed to download image {image_url}: {str(e)}")
        return None


def create_video_from_image(
    image_path: str,
    duration: float,
    output_path: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    apply_zoom: bool = True
) -> Optional[str]:
    """
    Convert a single image to a video clip with optional zoom effect.
    
    Args:
        image_path: Path to the source image
        duration: Duration of the video in seconds
        output_path: Path to save the output video
        video_aspect: Video aspect ratio
        apply_zoom: Whether to apply a zoom effect
        
    Returns:
        Path to the created video, or None if creation fails
    """
    try:
        from moviepy import ImageClip, CompositeVideoClip
        
        video_width, video_height = video_aspect.to_resolution()
        
        # Create image clip with specified duration
        clip = ImageClip(image_path).with_duration(duration).with_position("center")
        
        # Resize to fit aspect ratio
        clip_w, clip_h = clip.size
        clip_ratio = clip_w / clip_h
        video_ratio = video_width / video_height
        
        if clip_ratio > video_ratio:
            # Image is wider - fit to height
            scale_factor = video_height / clip_h
        else:
            # Image is taller - fit to width
            scale_factor = video_width / clip_w
        
        new_width = int(clip_w * scale_factor)
        new_height = int(clip_h * scale_factor)
        clip = clip.resized(new_size=(new_width, new_height))
        
        # Apply zoom effect if requested
        if apply_zoom:
            zoom_factor = 1 + (duration * 0.03)
            clip = clip.resized(lambda t: 1 + (zoom_factor - 1) * (t / duration))
        
        # Composite on black background for proper sizing
        from moviepy import ColorClip
        background = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(duration)
        clip = clip.with_position("center")
        final_clip = CompositeVideoClip([background, clip])
        
        # Write video
        final_clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            bitrate="8000k",
            audio_bitrate="320k",
            logger=None,
            ffmpeg_params=["-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"]
        )
        
        # Clean up
        video.close_clip(clip)
        video.close_clip(final_clip)
        video.close_clip(background)
        
        logger.info(f"Created video from image: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to create video from image: {str(e)}")
        return None


def get_segment_visual(
    segment: ScriptSegment,
    segment_duration: float,
    image_links: List[str],
    task_dir: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_source: str = "pexels",
    allowed_image_indices: List[int] = []
) -> Optional[str]:
    """
    Get video/image for a segment - either from article images or by searching.
    
    Args:
        segment: The script segment
        segment_duration: Duration needed for this segment's visual
        image_links: List of image URLs extracted from article
        task_dir: Directory for saving files
        video_aspect: Video aspect ratio
        video_source: Video search source (pexels/pixabay)
        allowed_image_indices: List of image indices (0-based) to allow using. 
                              If empty, no article images will be used.
        
    Returns:
        Path to the video file for this segment
    """
    if segment.has_image and segment.image_index is not None:
        # Check if this image index is allowed
        # segment.image_index is 1-based, convert to 0-based for checking
        image_idx = segment.image_index - 1
        
        if image_idx in allowed_image_indices:
            # Use article image
            if 0 <= image_idx < len(image_links):
                image_url = image_links[image_idx]
                logger.info(f"Using article image {segment.image_index} (Index {image_idx}): {image_url}")
                
                # Download image
                image_path = download_image(image_url, task_dir)
                if image_path:
                    # Convert to video
                    video_path = os.path.join(task_dir, f"segment-img-{segment.image_index}.mp4")
                    return create_video_from_image(
                        image_path, 
                        segment_duration, 
                        video_path, 
                        video_aspect
                    )
            else:
                logger.warning(f"Image index {segment.image_index} out of range (have {len(image_links)} images)")
        else:
            logger.info(f"Skipping article image {segment.image_index} (Index {image_idx} not in allowed list {allowed_image_indices})")
    
    # Search for video/image based on segment content
    search_terms = generate_segment_search_terms(segment.text)
    if not search_terms:
        logger.warning(f"No search terms generated for segment: {segment.text[:50]}...")
        return None
    
    logger.info(f"Searching for visuals with terms: {search_terms}")
    
    # Try to download videos for search terms
    downloaded_videos = material.download_videos(
        task_id="segment",
        search_terms=search_terms,
        source=video_source,
        video_aspect=video_aspect,
        audio_duration=segment_duration,
        max_clip_duration=int(segment_duration) + 1
    )
    
    if downloaded_videos:
        return downloaded_videos[0]
    
    # Fallback: search for images if no videos found
    logger.warning(f"No videos found, segment will need fallback visual")
    return None


async def process_article_to_segments(url: str, target_language: Optional[str] = None) -> Tuple[List[ScriptSegment], List[str], str]:
    """
    Process an article URL into script segments.
    
    Args:
        url: The article URL to process
        target_language: Optional language to translate the script into (e.g., "English")
        
    Returns:
        Tuple of (segments, image_links, title)
    """
    # Step 1: Parse URL to markdown
    logger.info(f"Parsing article URL: {url}")
    raw_markdown = await parse_url_to_markdown(url)
    if not raw_markdown:
        raise ValueError(f"Failed to parse URL: {url}")
    
    # Step 2: Extract post info (title + content)
    extracted = extract_post_info(raw_markdown)
    logger.info(f"Extracted post info: {len(extracted)} characters")
    print(extracted)

    # Step 3: Process markdown (replace images with $n$ patterns)
    cleaned_markdown, image_links = process_markdown(extracted)
    logger.info(f"Found {len(image_links)} images in article")
    print(cleaned_markdown)

    # Step 4: Translate if requested
    if target_language:
        logger.info(f"Translating article to {target_language}...")
        cleaned_markdown = translate_text(cleaned_markdown, target_lang=target_language)
    print(cleaned_markdown)

    # Step 5: Split into segments
    segments = get_script_segments(cleaned_markdown)
    logger.info(f"Created {len(segments)} script segments")
    
    # Extract title from first segment if it starts with #
    title = "Article Video"
    if segments and segments[0].text.startswith('#'):
        title = segments[0].text.lstrip('#').strip()
    print(title)
    return segments, image_links, title


def process_article_to_segments_sync(url: str, target_language: Optional[str] = None) -> Tuple[List[ScriptSegment], List[str], str]:
    """Synchronous wrapper for process_article_to_segments."""
    return asyncio.run(process_article_to_segments(url, target_language))


if __name__ == "__main__":
    # Test with sample URL
    # test_url = 'https://zhuanlan.zhihu.com/p/1970939067463104119'
    # test_url = 'https://zhuanlan.zhihu.com/p/1986191794870964353'
    print("Testing article processing...")
    segments, image_links, title = process_article_to_segments_sync(test_url)
    
    print(f"\nTitle: {title}")
    print(f"Image links: {len(image_links)}")
    for i, link in enumerate(image_links):
        print(f"  {i+1}: {link[:60]}...")
    
    print(f"\nSegments: {len(segments)}")
    for i, seg in enumerate(segments):
        print(f"\n--- Segment {i+1} ---")
        print(f"Has image: {seg.has_image}, Image index: {seg.image_index}")
        print(f"Text: {seg.text[:100]}...")
        
        if not seg.has_image:
            print("Generating search terms...")
            terms = generate_segment_search_terms(seg.text)
            print(f"Search terms: {terms}")
