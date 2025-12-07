# Article Video Generation - Visual Flowchart

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ARTICLE URL INPUT                           │
│                     (e.g., blog post, news)                         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: Parse to Markdown                        │
│  • Extract text content                                             │
│  • Find all images → [img1.jpg, img2.jpg, ...]                      │
│  • Replace images with markers: $1$, $2$, $3$                       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STEP 2: Split into Segments                        │
│  "Text before. $1$ More text. $2$ Final text."                      │
│  ↓                                                                   │
│  Segment 1: "Text before." [has_image=False]                        │
│  Segment 2: "More text."    [has_image=True, index=1]               │
│  Segment 3: "Final text."   [has_image=True, index=2]               │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                ┌────────────────┴──────────────┐
                │                               │
                ▼                               ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│   Segment WITHOUT Image   │   │    Segment WITH Image ($n$)  │
│   [has_image = False]     │   │    [has_image = True]        │
└───────────┬───────────────┘   └──────────────┬───────────────┘
            │                                   │
            ▼                                   ▼
   ┌────────────────────┐            ┌─────────────────────┐
   │  Generate Search   │            │  Download Article   │
   │  Terms via LLM     │            │  Image (nth image)  │
   │  ───────────────   │            │  ─────────────────  │
   │ ["ocean waves",    │            │  img-abc123.jpg     │
   │  "sunset beach"]   │            └──────────┬──────────┘
   └────────┬───────────┘                       │
            │                                   │
            ▼                                   ▼
   ┌────────────────────┐            ┌─────────────────────┐
   │  Download Stock    │            │  Convert Image      │
   │  Videos/Images     │            │  to Video Clip      │
   │  ───────────────   │            │  ─────────────────  │
   │  clip-xyz789.mp4   │            │  segment-img-1.mp4  │
   │  (from Pexels)     │            │  (with zoom effect) │
   └────────┬───────────┘            └──────────┬──────────┘
            │                                   │
            └──────────┬────────────────────────┘
                       │
                       ▼
        ╔══════════════════════════════╗
        ║  get_segment_visual() L219   ║  ← KEY FUNCTION
        ║  ────────────────────────     ║
        ║  Returns video clip for      ║
        ║  this segment (unified API)  ║
        ╚══════════════╦═══════════════╝
                       │
                       ▼
        ┌──────────────────────────────┐
        │    All Segment Video Clips   │
        │  [seg1.mp4, seg2.mp4, ...]   │
        └──────────────┬───────────────┘
                       │
        ┌──────────────┴───────────────┐
        │                              │
        ▼                              ▼
┌───────────────────┐      ┌────────────────────────┐
│  STEP 3:          │      │  STEP 4:               │
│  Generate Audio   │      │  Generate Subtitles    │
│  ───────────────  │      │  ──────────────────    │
│  TTS from full    │      │  Timing from voice     │
│  script text      │      │  and script            │
│  → audio.mp3      │      │  → subtitle.srt        │
└─────────┬─────────┘      └───────────┬────────────┘
          │                            │
          └──────────┬─────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   STEP 5: Combine Everything   │
        │   ──────────────────────────   │
        │   • Concatenate segment videos │
        │   • Add voiceover audio        │
        │   • Burn in subtitles          │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │       FINAL VIDEO OUTPUT       │
        │    (title_with_subs.mp4)      │
        │                                │
        │  Ready for social media or     │
        │  YouTube upload                │
        └────────────────────────────────┘
```

---

## Key Insight: The `get_segment_visual()` Function (Line 219)

The highlighted function acts as a **unified interface** that:

1. **Inspects the segment** to check if it has an embedded image marker
2. **Routes to appropriate handler**:
   - Image path: Downloads article image → Converts to video
   - Text-only path: Generates search terms → Fetches stock video
3. **Returns consistent output**: A video clip path, regardless of source
4. **Matches duration**: The clip duration matches the segment's narration time

This design allows the rest of the pipeline to treat all segments uniformly, even though they come from different sources (article images vs. stock videos).

---

## Data Flow Example

**Input Article:**
```markdown
# Ocean Conservation

Marine life is under threat. ![$1$]

Climate change affects coral reefs through rising temperatures.

Scientists are working on solutions. ![$2$]
```

**After Processing:**

| Segment # | Text | Has Image | Image Index | Visual Source |
|-----------|------|-----------|-------------|---------------|
| 1 | "Ocean Conservation" | No | - | Stock: "ocean conservation" |
| 2 | "Marine life is under threat." | Yes | 1 | Article image #1 |
| 3 | "Climate change affects coral reefs..." | No | - | Stock: "coral reef climate" |
| 4 | "Scientists are working on solutions." | Yes | 2 | Article image #2 |

**Output:**
- 4 video clips (mix of article images and stock videos)
- 1 voiceover audio file
- 1 subtitle file
- 1 final combined video

---

## Function Call Hierarchy

```
generate_article_video()                    # Main orchestration
├── process_article_to_segments_sync()      # Parse article
│   ├── parse_url_to_markdown()             # Get raw content
│   ├── extract_post_info()                 # Clean content
│   ├── process_markdown()                  # Extract images → $n$
│   └── get_script_segments()               # Split into segments
│
├── [For each segment]
│   └── get_segment_visual()                # ← LINE 219 (Key function)
│       ├── IF has_image:
│       │   ├── download_image()            # Get article image
│       │   └── create_video_from_image()   # Image → video
│       └── ELSE:
│           ├── generate_segment_search_terms()  # LLM search terms
│           └── material.download_videos()       # Stock videos
│
├── voice.create_voiceover()                # Generate TTS audio
├── subtitle.create_subtitle()              # Generate subtitles
├── video.combine_videos()                  # Merge segments + audio
└── video.add_subtitles()                   # Burn subtitles
```

---

## Timeline View

```
Time →  [0s ─────── 5s ─────── 10s ─────── 15s ─────── 20s]

Video:  [Segment 1  ][Segment 2  ][Segment 3  ][Segment 4  ]
        (stock vid) (article img)(stock vid) (article img)

Audio:  [────────────── Continuous voiceover ──────────────]

Subs:   [Text 1 ] [Text 2 ] [Text 3 ] [Text 4 ]
```

Each segment video is timed to match the duration of its narration portion in the voiceover.

---

## File Dependencies

```
article_video.py (L219: get_segment_visual)
├── Imports from app.services:
│   ├── material.py → download_videos()
│   ├── video.py → combine_videos(), add_subtitles()
│   └── voice.py → create_voiceover()
│
├── Imports from app.services.utils:
│   ├── url_parser.py → parse_url_to_markdown()
│   └── process_md.py → process_markdown(), get_script_segments()
│
└── Imports from app.models:
    └── schema.py → VideoAspect, MaterialInfo, etc.
```

---

This flowchart should help visualize how the new `get_segment_visual()` function (line 219) fits into the complete article-to-video pipeline!
