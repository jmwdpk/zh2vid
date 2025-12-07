
### 🆕 Article-to-Video Generation
**NEW!** Convert any article URL into an engaging video automatically.

This feature intelligently processes articles by:
- **Parsing content**: Extracts text and embedded images from article URLs
- **Smart segmentation**: Splits content into natural script segments
- **Intelligent visuals**: Uses article images when available, fetches relevant stock videos for text-only segments
- **Unified processing**: The `get_segment_visual()` function seamlessly handles both sources

**Quick Start:**
```bash
# Generate video from article URL
python generate_article_video.py --url "https://your-article-url.com"

# For landscape video (YouTube)
python generate_article_video.py --url "https://your-article.com" --aspect landscape

# See all options
python generate_article_video.py --help
```

**Documentation:**
- 📖 Quick Guide: [`ARTICLE_VIDEO_GUIDE.md`](ARTICLE_VIDEO_GUIDE.md)
- 📊 Workflow Diagram: [`WORKFLOW_DIAGRAM.md`](WORKFLOW_DIAGRAM.md)
- 📋 Full Workflow: [`.agent/workflows/article-video-generation.md`](.agent/workflows/article-video-generation.md)
