"""
Unit tests for article video generation modules.
Tests url_parser, process_md, and article_video services.
"""
import unittest
import os
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestProcessMd(unittest.TestCase):
    """Tests for process_md module."""
    
    def test_script_segment_with_image(self):
        """Test ScriptSegment correctly identifies image patterns."""
        from app.services.utils.process_md import get_script_segments
        
        test_md = "Money is a tool. ![]($1$)"
        segments = get_script_segments(test_md)
        
        self.assertEqual(len(segments), 1)
        self.assertTrue(segments[0].has_image)
        self.assertEqual(segments[0].image_index, 1)
        self.assertEqual(segments[0].text, "Money is a tool.")
    
    def test_script_segment_without_image(self):
        """Test ScriptSegment correctly handles segments without images."""
        from app.services.utils.process_md import get_script_segments
        
        test_md = "Investing early leads to compound growth."
        segments = get_script_segments(test_md)
        
        self.assertEqual(len(segments), 1)
        self.assertFalse(segments[0].has_image)
        self.assertIsNone(segments[0].image_index)
    
    def test_mixed_segments(self):
        """Test processing of markdown with mixed image and non-image segments."""
        from app.services.utils.process_md import get_script_segments
        
        test_md = """
# Title

First paragraph without image.

Second paragraph with image. ![]($1$)

Third paragraph without image.

Fourth paragraph with different image. ![]($2$)
"""
        segments = get_script_segments(test_md)
        
        # Should have Title + 4 content segments = 5 segments
        self.assertGreaterEqual(len(segments), 4)
        
        # Find segments with images
        image_segments = [s for s in segments if s.has_image]
        self.assertEqual(len(image_segments), 2)
        
        # Verify image indices
        indices = [s.image_index for s in image_segments]
        self.assertIn(1, indices)
        self.assertIn(2, indices)
    
    def test_process_markdown_extracts_images(self):
        """Test that process_markdown correctly extracts image links."""
        from app.services.utils.process_md import process_markdown
        
        test_md = "Text with image ![](https://pic1.zhimg.com/test.jpg) and another ![](https://pic2.zhimg.com/other.jpg)"
        cleaned, image_links = process_markdown(test_md)
        
        self.assertEqual(len(image_links), 2)
        self.assertIn("$1$", cleaned)
        self.assertIn("$2$", cleaned)


class TestUrlParser(unittest.TestCase):
    """Tests for url_parser module."""
    
    def test_parse_url_function_exists(self):
        """Test that parse_url_to_markdown function exists and is importable."""
        from app.services.utils.url_parser import parse_url_to_markdown, parse_url_sync
        
        self.assertTrue(callable(parse_url_to_markdown))
        self.assertTrue(callable(parse_url_sync))


class TestArticleVideo(unittest.TestCase):
    """Tests for article_video module (syntax only, requires full env for imports)."""
    
    def test_module_syntax(self):
        """Test that article_video.py has valid Python syntax."""
        article_video_path = Path(__file__).parent.parent.parent / "app/services/article_video.py"
        
        with open(article_video_path, 'r') as f:
            code = f.read()
        
        # This will raise SyntaxError if code is invalid
        compile(code, article_video_path, 'exec')


if __name__ == "__main__":
    unittest.main()
