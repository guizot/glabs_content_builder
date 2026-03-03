import re
import requests
from bs4 import BeautifulSoup
from typing import List

from src.features.base_feature import BaseFeature


class ScraperFeature(BaseFeature):
    """
    ScraperFeature extracts URLs from a given text prompt, 
    scrapes their article content, and returns the combined context.
    """

    def execute(self, text_prompt: str) -> str:
        """
        Inputs: text_prompt (str) containing potential URLs.
        Outputs: combined scraped context (str).
        """
        urls = self._extract_urls(text_prompt)
        if not urls:
            return ""

        context = ""
        for url in urls:
            print(f"  🕸️ Scraping context from: {url}")
            article_text = self._fetch_and_extract_text(url)
            if article_text:
                context += f"\n--- Content from {url} ---\n{article_text}\n"

        return context

    def _extract_urls(self, text: str) -> List[str]:
        """Find all URLs in a given text using regex."""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)

    def _fetch_and_extract_text(self, url: str) -> str:
        """Fetch a URL and extract text from paragraphs."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Kill all script and style elements
            for script in soup(["script", "style"]):
                script.extract()    # rip it out

            # Extract text from p tags as they usually contain the main article body
            paragraphs = soup.find_all('p')
            text = ' '.join(p.get_text() for p in paragraphs)

            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # Truncate string if too long to save tokens (e.g. 5000 chars)
            max_chars = 5000
            if len(text) > max_chars:
                text = text[:max_chars] + "...\n[Content Truncated]"

            return text

        except Exception as e:
            print(f"  ⚠️ Warning: Failed to scrape {url}. Error: {e}")
            return ""
