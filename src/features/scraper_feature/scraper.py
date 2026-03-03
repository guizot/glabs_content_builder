import re
import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List, Optional

from src.features.base_feature import BaseFeature


class ScraperFeature(BaseFeature):
    """
    ScraperFeature extracts URLs from a given text prompt, 
    scrapes their article content, and returns the combined context.
    Also attempts to download the article's header/featured image.
    """

    def execute(self, text_prompt: str, output_dir: str = "outputs") -> dict:
        """
        Inputs: text_prompt (str) containing potential URLs.
        Outputs: dict with keys:
            - "context" (str): combined scraped text context.
            - "image_path" (str or None): path to downloaded header image, if found.
        """
        urls = self._extract_urls(text_prompt)
        if not urls:
            return {"context": "", "image_path": None}

        context = ""
        image_path = None

        for url in urls:
            print(f"  🕸️ Scraping context from: {url}")
            result = self._fetch_and_extract(url)
            if result["text"]:
                context += f"\n--- Content from {url} ---\n{result['text']}\n"
            # Use the first successfully downloaded image
            if image_path is None and result["image_url"]:
                image_path = self._download_image(result["image_url"], output_dir)

        return {"context": context, "image_path": image_path}

    def _extract_urls(self, text: str) -> List[str]:
        """Find all URLs in a given text using regex."""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)

    def _fetch_and_extract(self, url: str) -> dict:
        """Fetch a URL and extract article text + header image URL."""
        result = {"text": "", "image_url": None}
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Extract header image ---
            result["image_url"] = self._extract_header_image(soup, url)

            # Kill all script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Extract text from p tags
            paragraphs = soup.find_all('p')
            text = ' '.join(p.get_text() for p in paragraphs)

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            max_chars = 5000
            if len(text) > max_chars:
                text = text[:max_chars] + "...\n[Content Truncated]"

            result["text"] = text

        except Exception as e:
            print(f"  ⚠️ Warning: Failed to scrape {url}. Error: {e}")

        return result

    def _extract_header_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Try to find the article's main/header image from meta tags or content.
        Priority:
          1. og:image meta tag
          2. twitter:image meta tag
          3. First large <img> in the article
        """
        # 1. Open Graph image
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            img_url = og_img["content"]
            print(f"  🖼️ Found og:image: {img_url[:80]}...")
            return urljoin(base_url, img_url)

        # 2. Twitter card image
        tw_img = soup.find("meta", attrs={"name": "twitter:image"})
        if tw_img and tw_img.get("content"):
            img_url = tw_img["content"]
            print(f"  🖼️ Found twitter:image: {img_url[:80]}...")
            return urljoin(base_url, img_url)

        # 3. First reasonably large <img> in the page
        for img_tag in soup.find_all("img", src=True):
            src = img_tag["src"]
            # Skip tiny icons, tracking pixels, logos
            width = img_tag.get("width", "")
            height = img_tag.get("height", "")
            if width and width.isdigit() and int(width) < 200:
                continue
            if height and height.isdigit() and int(height) < 200:
                continue
            # Skip common non-article patterns
            src_lower = src.lower()
            if any(skip in src_lower for skip in ["logo", "icon", "avatar", "badge", "sprite", "1x1", "pixel"]):
                continue
            print(f"  🖼️ Found img tag: {src[:80]}...")
            return urljoin(base_url, src)

        print("  ℹ️ No header image found for this article.")
        return None

    def _download_image(self, image_url: str, output_dir: str) -> Optional[str]:
        """Download an image from a URL and save it to output_dir."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()

            # Determine file extension from content type
            content_type = response.headers.get("Content-Type", "")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"

            image_path = os.path.join(output_dir, f"article_header{ext}")

            with open(image_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)

            print(f"  ✅ Downloaded header image: {image_path}")
            return image_path

        except Exception as e:
            print(f"  ⚠️ Warning: Failed to download image from {image_url}. Error: {e}")
            return None
