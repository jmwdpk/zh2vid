---
description: End-to-end workflow for generating videos from article URLs
---

# Article-to-Video Generation Workflow

This workflow uses the new segment-based approach implemented in `article_video.py` (particularly the `get_segment_visual` function at line 219) to create videos from article URLs.

## Overview

The article video generation pipeline consists of these main stages:

1. **Article Parsing** - Convert article URL to structured markdown
2. **Segment Processing** - Split content into script segments with image markers
3. **Visual Material Generation** - Get appropriate videos/images for each segment
4. **Audio Generation** - Create voiceover from script text
5. **Final Assembly** - Combine visuals, audio, and subtitles

## Key Innovation: Segment-Based Visual Processing

The `get_segment_visual()` function (line 219) intelligently handles two types of segments:

- **Segments with embedded images** (`$n$` pattern): Uses the article's nth image, converted to video
- **Segments without images**: Generates search terms via LLM and fetches relevant stock videos/images

---

## Quick Start Example

### Test the Article Processing Pipeline

```python
# Run the test script to see article processing in action
cd /Users/mjiang/code/vidgen/videoGen
python -m app.services.article_video
```

This will:
- Parse a sample article URL
- Extract segments with image markers
- Generate search terms for non-image segments
- Display the processing results

---

## Step-by-Step End-to-End Workflow

### Step 1: Parse Article to Segments

```python
from app.services.article_video import process_article_to_segments_sync

# Your article URL (e.g., blog post, article, news piece)
article_url = "https://zhuanlan.zhihu.com/p/1970939067463104119"

# Parse and process the article
segments, image_links, title = process_article_to_segments_sync(article_url)

print(f"Title: {title}")
print(f"Found {len(segments)} segments")
print(f"Found {len(image_links)} images")
```

**What happens:**
- URL content is parsed to markdown
- Images are extracted and replaced with `$n$` markers
- Content is split into natural script segments
- Each segment knows if it has an associated image

### Step 2: Generate Visuals for Each Segment

```python
import os
from app.models.schema import VideoAspect
from app.services.article_video import get_segment_visual
from app.services import voice

# Create task directory for outputs
task_id = "article_video_test"
task_dir = os.path.join(config.app.get("storage_path", "./storage"), task_id)
os.makedirs(task_dir, exist_ok=True)

# Configuration
video_aspect = VideoAspect.portrait  # or VideoAspect.landscape
video_source = "pexels"  # or "pixabay"

# Process each segment
segment_videos = []
segment_durations = []

for i, segment in enumerate(segments):
    # Estimate duration based on text length (adjust as needed)
    # Rough estimate: ~150 words per minute = 2.5 words per second
    word_count = len(segment.text.split())
    segment_duration = max(2.0, word_count / 2.5)  # minimum 2 seconds
    
    print(f"\nProcessing segment {i+1}/{len(segments)}")
    print(f"Has image: {segment.has_image}, Image index: {segment.image_index}")
    print(f"Duration: {segment_duration:.1f}s")
    
    # Get visual for this segment
    video_path = get_segment_visual(
        segment=segment,
        segment_duration=segment_duration,
        image_links=image_links,
        task_dir=task_dir,
        video_aspect=video_aspect,
        video_source=video_source
    )
    
    if video_path:
        segment_videos.append(video_path)
        segment_durations.append(segment_duration)
        print(f"✓ Generated visual: {video_path}")
    else:
        print(f"✗ Failed to generate visual for segment {i+1}")
```

**What happens:**
- For segments with `$n$` markers: Downloads article's nth image → Converts to video with zoom effect
- For segments without images: Generates search terms → Downloads relevant stock videos
- Each segment gets a video clip matching its duration

### Step 3: Generate Audio/Voiceover

```python
from app.services import voice

# Combine all segment texts (excluding image markers)
full_script = "\n\n".join([seg.text for seg in segments])

# Generate voiceover
voice_name = "en-US-JennyNeural-Female"  # or your preferred voice
voice_rate = 1.0  # speaking rate

audio_file, audio_duration, sub_maker = voice.create_voiceover(
    text=full_script,
    voice_name=voice_name,
    voice_rate=voice_rate,
    task_id=task_id
)

print(f"Generated audio: {audio_file}")
print(f"Audio duration: {audio_duration:.1f}s")
```

**Alternatives:**
- Use Azure TTS, Edge TTS, or other voice services
- Adjust segment durations based on actual audio timing
- For better sync: Generate audio per segment, then adjust video durations

### Step 4: Generate Subtitles (Optional)

```python
from app.services import subtitle

# Generate subtitle file
subtitle_path = subtitle.create_subtitle(
    task_id=task_id,
    script=full_script,
    audio_file=audio_file,
    voice_name=voice_name,
    sub_maker=sub_maker
)

print(f"Generated subtitles: {subtitle_path}")
```

### Step 5: Combine Videos with Audio

```python
from app.services import video
from app.models.schema import VideoParams, VideoConcatMode

# Combine all segment videos
combined_video_path = os.path.join(task_dir, "combined_segments.mp4")

video.combine_videos(
    combined_video_path=combined_video_path,
    video_paths=segment_videos,
    audio_file=audio_file,
    video_aspect=video_aspect
)

print(f"Combined video: {combined_video_path}")
```

### Step 6: Add Subtitles (Optional)

```python
if subtitle_path:
    final_video_path = os.path.join(task_dir, "final_video_with_subs.mp4")
    
    video.add_subtitles(
        video_path=combined_video_path,
        subtitle_path=subtitle_path,
        output_path=final_video_path
    )
    
    print(f"Final video with subtitles: {final_video_path}")
else:
    final_video_path = combined_video_path
    print(f"Final video: {final_video_path}")
```

---

## Complete Example Script

Save this as `generate_article_video.py`:

```python
#!/usr/bin/env python
"""
Complete example: Generate video from article URL
"""
import os
import sys
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
    video_source: str = "pexels"
):
    """Generate a complete video from an article URL."""
    
    logger.info(f"Starting article video generation for: {article_url}")
    
    # 1. Parse article to segments
    logger.info("Step 1: Parsing article to segments...")
    segments, image_links, title = process_article_to_segments_sync(article_url)
    logger.info(f"Found {len(segments)} segments, {len(image_links)} images")
    
    # Setup task directory
    task_dir = os.path.join(config.app.get("storage_path", "./storage"), task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    # 2. Generate visuals for each segment
    logger.info("Step 2: Generating visuals for segments...")
    segment_videos = []
    
    for i, segment in enumerate(segments, 1):
        # Estimate duration (adjust based on your needs)
        word_count = len(segment.text.split())
        segment_duration = max(3.0, word_count / 2.5)
        
        logger.info(f"Processing segment {i}/{len(segments)}: {segment_duration:.1f}s")
        
        video_path = get_segment_visual(
            segment=segment,
            segment_duration=segment_duration,
            image_links=image_links,
            task_dir=task_dir,
            video_aspect=video_aspect,
            video_source=video_source
        )
        
        if video_path:
            segment_videos.append(video_path)
        else:
            logger.warning(f"Failed to get visual for segment {i}")
    
    if not segment_videos:
        logger.error("No segment videos generated!")
        return None
    
    # 3. Generate audio
    logger.info("Step 3: Generating voiceover...")
    full_script = "\n\n".join([seg.text for seg in segments])
    
    audio_file, audio_duration, sub_maker = voice.create_voiceover(
        text=full_script,
        voice_name=voice_name,
        voice_rate=voice_rate,
        task_id=task_id
    )
    
    if not audio_file:
        logger.error("Failed to generate audio!")
        return None
    
    logger.info(f"Generated audio: {audio_duration:.1f}s")
    
    # 4. Generate subtitles
    logger.info("Step 4: Generating subtitles...")
    subtitle_path = subtitle.create_subtitle(
        task_id=task_id,
        script=full_script,
        audio_file=audio_file,
        voice_name=voice_name,
        sub_maker=sub_maker
    )
    
    # 5. Combine videos
    logger.info("Step 5: Combining segment videos...")
    combined_video_path = os.path.join(task_dir, "combined_video.mp4")
    
    video.combine_videos(
        combined_video_path=combined_video_path,
        video_paths=segment_videos,
        audio_file=audio_file,
        video_aspect=video_aspect
    )
    
    # 6. Add subtitles
    if subtitle_path:
        logger.info("Step 6: Adding subtitles...")
        final_video_path = os.path.join(task_dir, f"{title[:50]}_final.mp4")
        
        video.add_subtitles(
            video_path=combined_video_path,
            subtitle_path=subtitle_path,
            output_path=final_video_path
        )
    else:
        final_video_path = combined_video_path
    
    logger.success(f"Video generation complete: {final_video_path}")
    return final_video_path


if __name__ == "__main__":
    # Example usage
    url = "https://zhuanlan.zhihu.com/p/1970939067463104119"
    
    final_video = generate_article_video(
        article_url=url,
        task_id="test_article_video",
        voice_name="en-US-JennyNeural-Female",
        video_aspect=VideoAspect.portrait
    )
    
    if final_video:
        print(f"\n✓ Success! Video saved to: {final_video}")
    else:
        print("\n✗ Failed to generate video")
```

Run it with:
```bash
// turbo
python generate_article_video.py
```

---

## Advanced: Integrate with Existing Task Pipeline

To integrate article video generation into the existing task system:

```python
from app.services.article_video import (
    process_article_to_segments_sync,
    get_segment_visual
)
from app.services.task import start
from app.models.schema import VideoParams

def generate_from_article_url(task_id: str, article_url: str, params: VideoParams):
    """
    Alternative workflow: Use article as content source for existing pipeline.
    """
    # 1. Parse article to get script
    segments, image_links, title = process_article_to_segments_sync(article_url)
    full_script = "\n\n".join([seg.text for seg in segments])
    
    # 2. Override params with article content
    params.video_subject = title
    params.video_script = full_script  # If supported, or use as-is
    
    # 3. Use existing task pipeline
    result = start(task_id, params, stop_at="video")
    
    return result
```

---

## Configuration Options

### Video Aspect Ratios
```python
from app.models.schema import VideoAspect

VideoAspect.portrait    # 9:16 (TikTok, Instagram Reels)
VideoAspect.landscape   # 16:9 (YouTube)
VideoAspect.square      # 1:1 (Instagram feed)
```

### Video Sources
- `"pexels"` - Pexels stock video library
- `"pixabay"` - Pixabay stock video library
- `"local"` - Use local video files

### Voice Options
Check available voices in your TTS service:
- Azure: `az cognitiveservices account list-skus`
- Edge TTS: Use `edge-tts --list-voices`

---

## Troubleshooting

### No videos found for segments
- Check that search terms are being generated (look at logs)
- Try different `video_source` (pexels vs pixabay)
- Verify API keys/credentials for video sources
- Fallback: Use article images for more segments

### Image download failures
- Check image URLs are accessible
- Verify SSL certificates (script uses `verify=False` for testing)
- Ensure adequate disk space

### Audio/video sync issues
- Generate audio per segment for precise timing
- Adjust word-per-second rate in duration calculation
- Use actual audio duration to trim/extend video clips

### Memory issues
- Process segments in batches
- Close video clips after processing
- Clear temp files periodically

---

## Next Steps

1. **Improve duration estimation**: Use actual TTS timing per segment
2. **Better visual matching**: Train custom search term generation
3. **Add transitions**: Use video.add_transitions() between segments
4. **Background music**: Add soundtrack with video.add_background_music()
5. **Custom branding**: Add intro/outro clips, watermarks
6. **Batch processing**: Process multiple articles in parallel

---

## Related Files

- `app/services/article_video.py` - Core article video logic (includes `get_segment_visual` at line 219)
- `app/services/utils/url_parser.py` - URL to markdown parsing
- `app/services/utils/process_md.py` - Markdown processing and segment extraction
- `app/services/material.py` - Video/image material downloading
- `app/services/video.py` - Video composition and editing
- `app/services/voice.py` - Text-to-speech generation
- `app/services/subtitle.py` - Subtitle generation

---

## Questions or Issues?

- Check logs for detailed error messages
- Run the test suite: `python -m pytest test/services/test_article_video.py`
- Review example in `article_video.py` `__main__` section (line 329)
