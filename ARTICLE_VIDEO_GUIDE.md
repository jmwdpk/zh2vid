# Article Video Generation - Quick Reference

## New Functionality (Line 219: `get_segment_visual`)

The key innovation in `article_video.py` is the **`get_segment_visual()`** function at line 219, which intelligently processes segments:

### How it Works

```python
def get_segment_visual(
    segment: ScriptSegment,
    segment_duration: float,
    image_links: List[str],
    task_dir: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_source: str = "pexels"
) -> Optional[str]:
```

**For segments WITH embedded images (`$n$` pattern):**
1. Extracts the image index from the segment
2. Downloads the article's nth image
3. Converts image to video with zoom effect
4. Duration matches segment timing

**For segments WITHOUT images:**
1. Uses LLM to generate search terms from segment text
2. Searches stock video libraries (Pexels/Pixabay)
3. Downloads relevant video clips
4. Returns best matching video for the segment

---

## Quick Start

### Run the Example Script

```bash
# Default test (uses sample article)
python generate_article_video.py

# Custom article URL
python generate_article_video.py --url "https://your-article-url.com"

# Landscape video for YouTube
python generate_article_video.py --aspect landscape

# See all options
python generate_article_video.py --help
```

---

## Pipeline Overview

```
Article URL
    ↓
[1] Parse to Markdown → Extract images → Replace with $n$ markers
    ↓
[2] Split into Segments → Each knows if it has an image
    ↓
[3] For Each Segment:
    • Has image? → Download & convert to video (get_segment_visual L219)
    • No image? → Generate search terms → Fetch stock video (get_segment_visual L219)
    ↓
[4] Generate Voiceover → TTS from combined script
    ↓
[5] Generate Subtitles → From voice timing
    ↓
[6] Combine All → Segments + Audio + Subtitles = Final Video
```

---

## Code Examples

### Minimal Example

```python
from app.services.article_video import (
    process_article_to_segments_sync,
    get_segment_visual
)

# Parse article
segments, images, title = process_article_to_segments_sync(url)

# Get visual for first segment
video = get_segment_visual(
    segment=segments[0],
    segment_duration=5.0,
    image_links=images,
    task_dir="./output"
)
```

### Complete Workflow

See `generate_article_video.py` for full implementation.

---

## Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `get_segment_visual()` | `article_video.py:219` | **Main innovation**: Get video for segment (article image OR stock video) |
| `process_article_to_segments()` | `article_video.py:288` | Parse URL → segments + images |
| `generate_segment_search_terms()` | `article_video.py:29` | LLM generates search terms for stock videos |
| `download_image()` | `article_video.py:96` | Download article images |
| `create_video_from_image()` | `article_video.py:140` | Convert static image to video with zoom |

---

## Configuration

### Video Aspects
```python
VideoAspect.portrait    # 9:16 for TikTok/Reels/Shorts
VideoAspect.landscape   # 16:9 for YouTube
VideoAspect.square      # 1:1 for Instagram
```

### Video Sources
- `"pexels"` - High-quality stock videos
- `"pixabay"` - Free stock videos

### Voice Examples
- `"en-US-JennyNeural-Female"` - US English (default)
- `"en-GB-SoniaNeural-Female"` - British English
- `"zh-CN-XiaoyiNeural-Female"` - Chinese Mandarin

---

## Workflow File

For detailed step-by-step instructions, see:
```
.agent/workflows/article-video-generation.md
```

Or use the slash command:
```
/article-video-generation
```

---

## Testing

```bash
# Test article parsing only
python -m app.services.article_video

# Run unit tests
python -m pytest test/services/test_article_video.py -v

# Test with custom article
python generate_article_video.py --url "YOUR_URL" --task-id "test_1"
```

---

## Output Structure

```
storage/
└── {task_id}/
    ├── img-{hash}.jpg              # Downloaded article images
    ├── segment-img-1.mp4           # Image-based segment videos
    ├── segment-img-2.mp4
    ├── clip-{hash}.mp4             # Stock video segments
    ├── audio.mp3                   # Generated voiceover
    ├── subtitle.srt                # Subtitle file
    ├── combined_video.mp4          # All segments combined
    └── {title}_with_subs.mp4       # Final video with subtitles
```

---

## Advanced: Custom Integration

```python
# Integrate into existing pipeline
from app.services import task
from app.services.article_video import process_article_to_segments_sync

def custom_article_video(article_url: str):
    # Get segments and script
    segments, images, title = process_article_to_segments_sync(article_url)
    script = "\n\n".join([seg.text for seg in segments])
    
    # Use existing task pipeline with article content
    params = VideoParams(
        video_subject=title,
        video_script=script,
        voice_name="en-US-JennyNeural-Female",
        # ... other params
    )
    
    result = task.start(task_id="custom_task", params=params)
    return result
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No videos found | Check API keys for Pexels/Pixabay; try different `video_source` |
| Image download fails | Verify image URLs are accessible; check network connection |
| Audio/video out of sync | Generate audio per segment; adjust `words_per_second` |
| Poor visual matching | Improve search terms; use more article images |

---

## What Makes Line 219 Special?

The `get_segment_visual()` function is the **core innovation** because it:

1. **Handles both cases** - article images AND stock videos in one unified interface
2. **Preserves article context** - Uses actual images from the article when available
3. **Intelligent fallback** - Generates semantically relevant search terms for text-only segments
4. **Consistent output** - Returns video clips regardless of source
5. **Flexible timing** - Adapts visual duration to match narration

This allows the pipeline to create cohesive videos from articles with **mixed content** (text + images), automatically finding appropriate visuals for every segment.

---

## Next Steps

1. ✅ Review workflow: `.agent/workflows/article-video-generation.md`
2. ✅ Run example: `python generate_article_video.py`
3. ✅ Test with your article: `--url "YOUR_ARTICLE_URL"`
4. 🔧 Customize: Modify voices, aspect ratios, search logic
5. 🚀 Integrate: Add to your existing video pipeline

---

**Questions?** Check the detailed workflow or examine `article_video.py` directly.
