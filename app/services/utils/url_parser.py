"""
URL Parser Module
Converts web article URLs to markdown content using crawl4ai.
"""
import asyncio
from typing import Optional
from loguru import logger

try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    logger.warning("crawl4ai not installed. URL parsing will not be available.")
    AsyncWebCrawler = None


async def parse_url_to_markdown(url: str) -> Optional[str]:
    """
    Parse URL content and return as markdown.
    
    Args:
        url: The URL to parse
        
    Returns:
        Markdown content as string, or None if parsing fails
    """
    if AsyncWebCrawler is None:
        logger.error("crawl4ai is not installed. Please install it with: pip install crawl4ai")
        return None
        
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.markdown:
                logger.info(f"Successfully parsed URL: {url}")
                return result.markdown
            else:
                logger.warning(f"No markdown content extracted from URL: {url}")
                return None
    except Exception as e:
        logger.error(f"Failed to parse URL {url}: {str(e)}")
        return None


def parse_url_sync(url: str) -> Optional[str]:
    """
    Synchronous wrapper for parse_url_to_markdown.
    
    Args:
        url: The URL to parse
        
    Returns:
        Markdown content as string, or None if parsing fails
    """
    return asyncio.run(parse_url_to_markdown(url))


if __name__ == "__main__":
    # Test with sample URL
    test_url = 'https://zhuanlan.zhihu.com/p/1970939067463104119'
    result = parse_url_sync(test_url)
    if result:
        print(f"Parsed {len(result)} characters of markdown")
        # Save for testing
        with open('data/test.md', 'w', encoding='utf-8') as f:
            f.write(result)
        print("Saved to data/test.md")