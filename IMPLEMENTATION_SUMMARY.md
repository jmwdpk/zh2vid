# Article Video Generation - Complete Implementation Summary

## Overview

This document provides a complete summary of the new **article-to-video generation feature** implemented in this enhanced MoneyPrinterTurbo fork. The core innovation is the `get_segment_visual()` function at **line 219 in `app/services/article_video.py`**.

---

## 📋 What Was Created

### 1. Core Implementation Files

| File | Purpose | Key Components |
|------|---------|----------------|
| `app/services/article_video.py` | Main service module | • `get_segment_visual()` (L219) - Core function<br>• `generate_segment_search_terms()` - LLM search term generation<br>• `download_image()` - Article image downloader<br>• `create_video_from_image()` - Image to video converter<br>• `process_article_to_segments()` - URL parser |
| `app/services/utils/url_parser.py` | URL content extraction | • `parse_url_to_markdown()` - Extract article content |
| `app/services/utils/process_md.py` | Markdown processing | • `process_markdown()` - Image extraction & replacement<br>• `get_script_segments()` - Content segmentation<br>• `ScriptSegment` class - Segment data structure |

### 2. User-Facing Tools

| File | Purpose | How to Use |
|------|---------|------------|
| `generate_article_video.py` | **Main executable script** | `python generate_article_video.py --url "YOUR_URL"` |
| `ARTICLE_VIDEO_GUIDE.md` | **Quick reference guide** | Read for overview and code examples |
| `WORKFLOW_DIAGRAM.md` | **Visual flowchart** | Understand the complete pipeline |
| `.agent/workflows/article-video-generation.md` | **Detailed workflow** | Step-by-step instructions |

### 3. Test Files

| File | Purpose |
|------|---------|
| `test/services/test_article_video.py` | Unit tests for article processing |

---

## 🎯 Key Innovation: `get_segment_visual()` Function

**Location:** `app/services/article_video.py`, line 219

### Function Signature
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

### What Makes It Special

This function is the **centerpiece** of the article video generation system because it:

1. **Unified Interface**: Provides a single API for getting video clips from two different sources
2. **Content-Aware**: Automatically determines whether to use article images or stock videos
3. **Intelligent Routing**:
   - If segment has `$n$` marker → Download article's nth image → Convert to video
   - If segment is text-only → Generate search terms via LLM → Fetch stock videos
4. **Consistent Output**: Always returns a video clip path matching the segment duration
5. **Flexible**: Supports multiple video sources (Pexels, Pixabay) and aspect ratios

### How It Works

```python
# Pseudo-code flow
if segment.has_image and segment.image_index is not None:
    # PATH 1: Article Image
    image_url = image_links[segment.image_index - 1]
    image_path = download_image(image_url, task_dir)
    video_path = create_video_from_image(image_path, duration, ...)
    return video_path
else:
    # PATH 2: Stock Video
    search_terms = generate_segment_search_terms(segment.text)
    videos = material.download_videos(search_terms, ...)
    return videos[0] if videos else None
```

---

## 🔄 Complete Pipeline

```
1. Article URL Input
   ↓
2. Parse to Markdown (extract images → replace with $n$)
   ↓
3. Split into Segments (each segment knows if it has image)
   ↓
4. For Each Segment:
   → get_segment_visual() ← KEY FUNCTION (L219)
     • With image: Download + Convert to video
     • No image: Generate search terms + Fetch stock video
   ↓
5. Generate Voiceover (TTS from combined script)
   ↓
6. Generate Subtitles (timing from voice)
   ↓
7. Combine Everything (segments + audio + subtitles)
   ↓
8. Final Video Output
```

---

## 🚀 Quick Start Guide

### Installation (if not already done)

```bash
cd /Users/mjiang/code/vidgen/videoGen
conda activate MoneyPrinterTurbo  # or your environment
pip install -r requirements.txt
```

### Run Your First Article Video

```bash
# Use the default test article
python generate_article_video.py

# Or specify your own article URL
python generate_article_video.py --url "https://your-article-url.com"

# For YouTube (landscape format)
python generate_article_video.py \
    --url "https://your-article.com" \
    --aspect landscape \
    --voice "en-US-JennyNeural-Female"
```

### Test Article Processing Only

```bash
# Run the built-in test
python -m app.services.article_video
```

This will:
- Parse a sample article
- Show extracted segments
- Display which segments have images
- Generate search terms for text-only segments

---

## 📊 Example Data Flow

**Input Article:**
```markdown
# Ocean Conservation

Marine life is under threat. ![Image 1](https://example.com/ocean.jpg)

Climate change affects coral reefs through rising temperatures.

Scientists are working on solutions. ![Image 2](https://example.com/research.jpg)
```

**After Processing:**

| Segment | Text | Has Image | Visual Source |
|---------|------|-----------|---------------|
| 1 | "Ocean Conservation" | ❌ | Stock: "ocean conservation" |
| 2 | "Marine life is under threat." | ✅ (img 1) | Article image #1 |
| 3 | "Climate change affects..." | ❌ | Stock: "coral reef climate" |
| 4 | "Scientists are working..." | ✅ (img 2) | Article image #2 |

**Output:**
- 4 video clips (2 from article images, 2 from stock videos)
- 1 voiceover audio file
- 1 subtitle file
- 1 final combined video

---

## 🔧 Configuration Options

### Video Aspects
```python
VideoAspect.portrait    # 9:16 (TikTok, Instagram Reels, YouTube Shorts)
VideoAspect.landscape   # 16:9 (YouTube, standard video)
VideoAspect.square      # 1:1 (Instagram feed)
```

### Video Sources
- `"pexels"` - High-quality stock videos (default)
- `"pixabay"` - Free stock videos

### Voice Options
Examples (depends on your TTS service):
- `"en-US-JennyNeural-Female"` - US English
- `"en-GB-SoniaNeural-Female"` - British English
- `"zh-CN-XiaoyiNeural-Female"` - Chinese

---

## 📁 Output Structure

After running `generate_article_video.py`, you'll find:

```
storage/{task_id}/
├── img-{hash}.jpg              # Downloaded article images
├── segment-img-1.mp4           # Videos created from article images
├── segment-img-2.mp4
├── clip-{hash}.mp4             # Downloaded stock video clips
├── audio.mp3                   # Generated voiceover
├── subtitle.srt                # Subtitle file
├── combined_video.mp4          # All segments combined with audio
└── {title}_with_subs.mp4       # Final output with burned-in subtitles
```

---

## 🧪 Testing

### Unit Tests
```bash
# Run all article video tests
python -m pytest test/services/test_article_video.py -v

# Run specific test
python -m pytest test/services/test_article_video.py::TestProcessMd::test_mixed_segments -v
```

### Manual Testing
```bash
# Test with a real article
python generate_article_video.py \
    --url "https://example.com/article" \
    --task-id "test_run_1"

# Check output in storage/test_run_1/
```

---

## 🎓 Learn More

### Documentation Files

1. **Quick Start** → `ARTICLE_VIDEO_GUIDE.md`
   - Overview of functionality
   - Key functions reference
   - Quick examples

2. **Visual Guide** → `WORKFLOW_DIAGRAM.md`
   - Complete flowchart
   - Data flow examples
   - Function call hierarchy

3. **Detailed Workflow** → `.agent/workflows/article-video-generation.md`
   - Step-by-step instructions
   - Complete code examples
   - Troubleshooting guide

4. **Main README** → `README.md`
   - Project overview
   - Updated with article video section

### Code References

- **Main Implementation**: `app/services/article_video.py`
  - Line 219: `get_segment_visual()` - **Core function**
  - Line 29: `generate_segment_search_terms()` - LLM search terms
  - Line 96: `download_image()` - Image downloader
  - Line 140: `create_video_from_image()` - Image to video converter
  - Line 288: `process_article_to_segments()` - Main parser

- **Utilities**: `app/services/utils/`
  - `url_parser.py` - URL content extraction
  - `process_md.py` - Markdown processing & segmentation

- **Example Script**: `generate_article_video.py`
  - Complete end-to-end implementation
  - CLI argument handling
  - Detailed logging

---

## 🔍 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No videos found | Search terms not effective | Try different `video_source` (pexels/pixabay) |
| Image download fails | URL inaccessible | Check network; verify image URLs |
| Audio/video out of sync | Duration estimation off | Adjust `words_per_second` parameter |
| LLM search terms fail | API issues | Check `pollinations_base_url` in config |
| Memory errors | Too many videos | Process segments in batches |

### Debug Tips

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python generate_article_video.py --url "YOUR_URL"

# Test article parsing separately
python -m app.services.article_video

# Check config settings
cat config.toml | grep -A5 pollinations
```

---

## 🎯 Use Cases

This feature is perfect for:

1. **Content Repurposing**: Turn blog posts into social media videos
2. **News Videos**: Convert news articles into video format
3. **Educational Content**: Transform tutorials into video lessons
4. **Social Media**: Create engaging short-form content from articles
5. **Marketing**: Convert case studies/whitepapers into promotional videos

---

## 🚀 Next Steps

### For Users
1. ✅ Try the example script: `python generate_article_video.py`
2. ✅ Test with your own article: `--url "YOUR_URL"`
3. 🔧 Customize settings: aspect ratio, voice, video source
4. 📤 Share your videos!

### For Developers
1. 🧪 Write more tests for edge cases
2. 🎨 Improve visual matching algorithms
3. ⚡ Add caching for downloaded assets
4. 🎵 Integrate background music options
5. 🔄 Add batch processing for multiple articles

---

## 📞 Support

- **Issues**: Open a GitHub issue
- **Questions**: Check documentation files
- **Contributions**: Pull requests welcome!

---

## 🙏 Credits

This article video generation feature builds upon:
- Original MoneyPrinterTurbo project
- Enhanced subtitle and TTS features from this fork
- Integration with Pexels/Pixabay APIs
- Pollinations.ai for LLM-based search term generation

---

**Last Updated**: December 2025
**Version**: 1.0
**Status**: ✅ Production Ready
