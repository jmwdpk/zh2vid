# Per-Segment Video Generation - Implementation Plan

## Current (Wrong) Architecture:

```
Segments → [Visual1, Visual2, Visual3, ...]
         ↓
Full Script → [One Big Audio File]
         ↓
Full Script → [One Big Subtitle File]
         ↓
Combine: [All Visuals] + [Big Audio] + [Big Subtitles]
         ↓
Result: Duration mismatches, sync issues
```

**Problems:**
- Visuals are generated with **estimated** durations (word_count / words_per_second)
- Audio is generated for **entire script** at once
- Visual duration ≠ Audio duration → requires looping/stretching
- If one segment fails visual generation, total video is shorter than audio

## Proposed (Correct) Architecture:

```
For each segment:
  1. Generate audio for segment text → Get ACTUAL duration
  2. Generate visual with EXACT audio duration
  3. Generate subtitle for segment audio
  4. Merge: Visual + Audio + Subtitle → Final Segment Video
  
Concatenate all final segment videos → Complete Video
```

**Benefits:**
- ✅ Perfect duration matching (visual duration = audio duration)
- ✅ No looping/stretching needed
- ✅ Each segment is self-contained
- ✅ Easy to regenerate individual segments
- ✅ Better error recovery

## Implementation Changes Needed:

### 1. Modify `generate_article_video.py`

**Current Step 2 (Generate Visuals):**
```python
for segment in segments:
    estimated_duration = word_count / words_per_second  # ❌ Estimation
    video_path = get_segment_visual(segment, estimated_duration, ...)
    segment_videos.append(video_path)
```

**New Step 2 (Generate Per-Segment Complete Videos):**
```python
final_segment_videos = []

for i, segment in enumerate(segments):
    # 2a. Generate audio for THIS segment
    segment_audio, actual_duration, segment_submaker = voice.create_voiceover(
        text=segment.text,
        voice_name=voice_name,
        voice_rate=voice_rate,
        task_id=f"{task_id}_seg{i}"
    )
    
    # 2b. Generate visual with EXACT audio duration
    segment_visual = get_segment_visual(
        segment=segment,
        segment_duration=actual_duration,  # ✅ Actual, not estimated
        ...
    )
    
    # 2c. Generate subtitle for THIS segment
    segment_subtitle = subtitle.create_subtitle(
        task_id=f"{task_id}_seg{i}",
        script=segment.text,
        audio_file=segment_audio,
        voice_name=voice_name,
        sub_maker=segment_submaker
    )
    
    # 2d. Merge visual + audio + subtitle → final segment video
    final_segment_path = os.path.join(task_dir, f"final_segment_{i:03d}.mp4")
    video.generate_video(
        video_path=segment_visual,
        audio_path=segment_audio,
        subtitle_path=segment_subtitle,
        output_file=final_segment_path,
        params=params
    )
    
    final_segment_videos.append(final_segment_path)
```

**New Step 3 (Concatenate Final Segments):**
```python
from moviepy import VideoFileClip, concatenate_videoclips

clips = [VideoFileClip(p) for p in final_segment_videos]
final_video = concatenate_videoclips(clips, method="compose")
final_video.write_videofile(output_path, ...)
```

### 2. Remove Old Steps

**Delete:**
- Step 3: Generate full audio
- Step 4: Generate full subtitle
- Step 5: Combine videos (old way)
- Step 6: Add subtitles (old way)

**Keep:**
- Step 1: Parse article to segments
- Step 2: Generate per-segment complete videos (NEW)
- Step 3: Concatenate final segments (NEW)

## Code Changes Required:

### Files to Modify:
1. `generate_article_video.py` - Main workflow
2. `app/services/voice.py` - Ensure `create_voiceover` works for short segments
3. `app/services/subtitle.py` - Ensure `create_subtitle` works for short segments

### New Helper Function (Optional):
```python
def create_complete_segment_video(
    segment: ScriptSegment,
    segment_index: int,
    task_dir: str,
    voice_name: str,
    voice_rate: float,
    video_aspect: VideoAspect,
    video_source: str,
    image_links: List[str],
    allowed_image_indices: List[int]
) -> Optional[str]:
    """
    Create a complete segment video with visual, audio, and subtitles.
    Returns path to final segment video.
    """
    # Implementation as shown above
```

## Migration Strategy:

1. **Create new function** `create_complete_segment_video()` in `article_video.py`
2. **Test with single segment** to verify audio/visual/subtitle sync
3. **Update main workflow** to use new per-segment approach
4. **Remove old code** after verification

## Expected Results:

- ✅ Each segment video has perfect audio/visual sync
- ✅ Total video duration = sum of segment durations
- ✅ No duration mismatches or looping artifacts
- ✅ Subtitles perfectly aligned with speech
- ✅ Easier debugging and regeneration
