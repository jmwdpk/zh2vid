import re
import requests
from urllib.parse import quote
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


# Read the content of test.md
def read_md_file(file_path="test.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as md_file:
            content = md_file.read()
            print(content)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")



def extract_post_info(res):
    # Assuming res is a string (use res.content or str(res) if needed)
    text = str(res)

    # Extract the title (between 登录/注册 and 切换模式)
    title_pattern = r"登录/注册\s*(.*?)\s*切换模式"
    title_match = re.search(title_pattern, text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "标题未找到"

    # Extract the main post content (between 已认证机构号 and 发布于)
    content_pattern = r"已认证机构号\s*(.*?)\s*发布于"
    content_match = re.search(content_pattern, text, re.DOTALL)
    content = content_match.group(1).strip() if content_match else "正文未找到"

    # Return in markdown format
    markdown_result = f"# {title}\n\n{content}"
    return markdown_result


# remove all search?content_id links in () and replace specific image links with their index


def process_markdown(markdown_output):
    # Extract image links
    image_links = re.findall(r'https://.*?zhimg\.com/.*?\.jpg', markdown_output)

    cleaned_output = markdown_output

    # Replace image links with their index
    for i, link in enumerate(image_links):
        cleaned_output = cleaned_output.replace(link, f'${i+1}$', 1) # Replace only the first occurrence

    # Remove the specified search links in parentheses
    cleaned_output = re.sub(r'\((https://zhida\.zhihu\.com/search\?content_id=.*?&zd_token=.*?)\)', '', cleaned_output)

    return cleaned_output, image_links



#translate the cleaned markdown to a youtube short script
def translate_to_script(cleaned_output):
    # remove word: upvote
    prompt = f"translate {cleaned_output}   in financially professional english(re-word if necessary) to generate a script ,   that can be used for creating \
    a finance youtube short video, remove special characters like: >  keep the paragraph/bullet structure of the input, make sure to keep the pattern like ![]($number$) in place as is, but do not add any extra words \
    split the result as title and content, separated by: a number + 'upvote', save the output as json"

    url = f"https://text.pollinations.ai/{quote(prompt)}"

    print(url)

    params = {"model": "openai"}

    # Get the response
    response = requests.get(url, params=params)
    return response.json()


def split_markdown_for_video_with_image_split(text, max_words=150):
    """
    Splits markdown text into semantic segments of at most max_words each.
    Respects paragraph boundaries, bullet points, and semantic structure.

    Special handling for image patterns:
    - If a segment contains ![]($n$) pattern in the middle, it will be split so that:
      * Text before + image pattern becomes one segment (image at the end)
      * Text after image pattern becomes the next segment
    - This maintains proper ordering with all subsequent segments

    Args:
        text: The markdown text to split
        max_words: Maximum words per segment (default 150)

    Returns:
        List of text segments with proper ordering maintained
    """
    import re

    # Helper function to split long text at sentence boundaries
    def split_long_text(text, max_words):
        """Helper function to split long text at sentence boundaries."""
        sentence_pattern = r'([.!?])\s+'
        parts = re.split(sentence_pattern, text)

        # Recombine sentences with punctuation
        sentences = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1] in '.!?':
                sentences.append(parts[i] + parts[i + 1])
                i += 2
            else:
                if parts[i].strip():
                    sentences.append(parts[i])
                i += 1

        # Combine sentences to stay under max_words
        segments = []
        current_segment = ""
        current_word_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = len(sentence.split())

            if sentence_words > max_words:
                if current_segment:
                    segments.append(current_segment.strip())
                    current_segment = ""
                    current_word_count = 0
                segments.append(sentence)
            elif current_word_count + sentence_words > max_words:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
                current_word_count = sentence_words
            else:
                if current_segment:
                    current_segment += ' ' + sentence
                else:
                    current_segment = sentence
                current_word_count += sentence_words

        if current_segment.strip():
            segments.append(current_segment.strip())

        return segments

    # Split into lines while preserving structure
    lines = text.strip().split('\n')

    # Group lines into logical blocks (paragraphs, bullets, headers)
    blocks = []
    current_block = []

    for line in lines:
        stripped = line.strip()

        # Empty line signals end of block
        if not stripped:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
        # Header line - make it its own block
        elif stripped.startswith('#'):
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            blocks.append(stripped)
        # Bullet point or list item
        elif stripped.startswith('-') or stripped.startswith('*') or re.match(r'^\d+\.', stripped):
            if current_block and not (current_block[-1].strip().startswith('-') or
                                     current_block[-1].strip().startswith('*') or
                                     re.match(r'^\d+\.', current_block[-1].strip())):
                blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        # Regular text
        else:
            current_block.append(line)

    if current_block:
        blocks.append('\n'.join(current_block))

    # Process each block
    segments = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        word_count = len(block.split())

        if word_count <= max_words:
            segments.append(block)
        else:
            lines_in_block = block.split('\n')

            if any(l.strip().startswith('-') or l.strip().startswith('*') or
                   re.match(r'^\d+\.', l.strip()) for l in lines_in_block):

                current_segment = ""
                current_words = 0

                for line in lines_in_block:
                    line_words = len(line.split())

                    if line_words > max_words:
                        if current_segment:
                            segments.append(current_segment.strip())
                            current_segment = ""
                            current_words = 0
                        split_line = split_long_text(line, max_words)
                        segments.extend(split_line)
                    elif current_words + line_words > max_words:
                        if current_segment:
                            segments.append(current_segment.strip())
                        current_segment = line
                        current_words = line_words
                    else:
                        if current_segment:
                            current_segment += '\n' + line
                        else:
                            current_segment = line
                        current_words += line_words

                if current_segment.strip():
                    segments.append(current_segment.strip())
            else:
                split_text = split_long_text(block, max_words)
                segments.extend(split_text)

    # NOW: Post-process to split segments containing image patterns
    # Key change: text before + image pattern stay together, text after becomes new segment
    final_segments = []
    image_pattern = r'!\[\]\(\$\d+\$\)'

    for segment in segments:
        # Check if segment contains an image pattern
        match = re.search(image_pattern, segment)

        if match:
            # Text before the image (including the image)
            before_and_image = segment[:match.end()].strip()
            # Text after the image
            after_text = segment[match.end():].strip()

            # Add text before + image pattern as one segment
            if before_and_image:
                final_segments.append(before_and_image)

            # Add text after image as separate segment (if exists)
            if after_text:
                final_segments.append(after_text)
        else:
            # No image pattern, keep segment as is
            final_segments.append(segment)
    return final_segments


@dataclass
class ScriptSegment:
    """
    Represents a segment of script for video generation.
    
    Attributes:
        text: The segment text (voiceover script, with image pattern removed if present)
        image_index: Image number if $n$ pattern was found (1-indexed), None otherwise
        has_image: Whether this segment should use an article image
        raw_text: Original segment text including image pattern if present
    """
    text: str
    image_index: Optional[int]
    has_image: bool
    raw_text: str


def get_script_segments(markdown_text: str, max_words: int = 150) -> List[ScriptSegment]:
    """
    Process markdown text and return structured script segments.
    
    Each segment includes:
    - Clean text for voiceover (image patterns removed)
    - Image index if the segment references an article image
    - Flag indicating whether to use article image or search for visuals
    
    Args:
        markdown_text: The processed markdown text (after process_markdown)
        max_words: Maximum words per segment
        
    Returns:
        List of ScriptSegment objects
    """
    # Get raw segments
    raw_segments = split_markdown_for_video_with_image_split(markdown_text, max_words)
    
    # Image pattern regex - matches ![]($n$) where n is a number
    image_pattern = r'!\[\]\(\$(\d+)\$\)'
    
    script_segments = []
    
    for raw_text in raw_segments:
        # Check for image pattern
        match = re.search(image_pattern, raw_text)
        
        if match:
            # Extract image index (1-indexed)
            image_index = int(match.group(1))
            # Remove image pattern from text for voiceover
            clean_text = re.sub(image_pattern, '', raw_text).strip()
            # Clean up extra whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            segment = ScriptSegment(
                text=clean_text,
                image_index=image_index,
                has_image=True,
                raw_text=raw_text
            )
        else:
            # No image pattern - will need to search for visuals
            clean_text = raw_text.strip()
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            segment = ScriptSegment(
                text=clean_text,
                image_index=None,
                has_image=False,
                raw_text=raw_text
            )
        
        # Only add non-empty segments
        if segment.text:
            script_segments.append(segment)
            logger.debug(f"Segment: has_image={segment.has_image}, image_index={segment.image_index}, text_preview='{segment.text[:50]}...'")
    
    logger.info(f"Processed {len(script_segments)} script segments")
    return script_segments
