import os
import asyncio
import aiohttp
from typing import Optional

from src.features.base_feature import BaseFeature

class ImageGenFeature(BaseFeature):
    """
    ImageGenFeature connects to HuggingFace Inference API to generate images 
    based on a text prompt, and downloads them to the specified output directory.
    """

    def __init__(self):
        self.api_key = os.environ.get("HUGGINGFACE_API_KEY")
        self.model = os.environ.get("IMAGE_GEN_MODEL", "black-forest-labs/FLUX.1-schnell")

        if not self.api_key:
            print("  ⚠️ HUGGINGFACE_API_KEY is not set in the environment. Image generation might fail or be rate-limited.")

    async def _generate_async(self, prompt: str, output_dir: str) -> Optional[str]:
        api_url = f"https://router.huggingface.co/hf-inference/models/{self.model}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        print(f"  🎨 Requesting image generation natively using HF...")
        print(f"  🤖 Model: {self.model}")
        print(f"  📝 Image prompt: '{prompt}'")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "inputs": prompt,
                    "parameters": {"width": 1024, "height": 576}
                }
                async with session.post(api_url, headers=headers, json=payload, ssl=False) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        
                        # Ensure output directory exists
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, "generated_header.png")
                        
                        with open(output_path, "wb") as f:
                            f.write(image_bytes)
                            
                        print(f"  ✅ Image saved successfully: {output_path}")
                        return output_path
                    else:
                        error_text = await response.text()
                        print(f"  ❌ Failed to generate image. HTTP {response.status}: {error_text}")
                        return None

        except Exception as e:
            print(f"  ❌ Failed to generate or download image: {e}")
            return None

    def execute(self, prompt: str, output_dir: str) -> Optional[str]:
        """
        Synchronous wrapper around the async generation method.
        """
        if not prompt:
            return None
            
        try:
            # Create a new event loop if one is already running (e.g. nested in another async context)
            # or use asyncio.run if we are in a purely sync context.
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(self._generate_async(prompt, output_dir))
                else:
                    return asyncio.run(self._generate_async(prompt, output_dir))
            except RuntimeError:
                return asyncio.run(self._generate_async(prompt, output_dir))
                
        except Exception as e:
            print(f"  ❌ Error executing ImageGenFeature: {e}")
            return None
