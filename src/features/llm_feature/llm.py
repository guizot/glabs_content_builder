import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Union

from src.features.base_feature import BaseFeature
from src.features.llm_feature.prompt import SYSTEM_PROMPT


class LLMFeature(BaseFeature):
    """
    LLMFeature is responsible for taking a user text prompt and optional 
    scraped context, and returning a structured JSON batch using an LLM.
    """

    def __init__(self, model: str = None):
        load_dotenv()
        self.model = model or os.environ.get("OPENAI_MODEL", "arcee-ai/trinity-large-preview:free")
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    def execute(self, user_prompt: str, context: str = "") -> Dict[str, Any]:
        """
        Inputs: 
            - user_prompt (str): The raw text prompt.
            - context (str): Extracted context from URLs.
        Outputs:
            - Dictionary containing "caption" (str) and "slides" (List of dicts) ready for CanvasFeature.
        """
        # Combine user prompt and context if available
        final_prompt = user_prompt
        if context:
            final_prompt += f"\n\nAdditional Context Provided by User:\n{context}"

        print(f"  🧠 Calling LLM ({self.model})...")
        print(f"  🌐 Using Base URL: {self.client.base_url}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0.7,
            )
            
            raw_text = response.choices[0].message.content
            
            # Clean up Markdown JSON blocks if the LLM ignored instruction #1
            raw_text = raw_text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            parsed = json.loads(raw_text.strip())
            
            if isinstance(parsed, list):
                return {"caption": "", "slides": parsed}
            elif isinstance(parsed, dict) and "slides" in parsed:
                if not isinstance(parsed["slides"], list):
                    parsed["slides"] = [parsed["slides"]]
                return parsed
            elif isinstance(parsed, dict):
                # Fallback if structure is weird
                return {"caption": parsed.get("caption", ""), "slides": []}
            else:
                return {"caption": "", "slides": []}
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Failed to parse LLM response as JSON: {e}")
            print(f"  Raw response: {raw_text}")
            return {"caption": "", "slides": []}
        except Exception as e:
            print(f"  ❌ Failed to call LLM: {str(e)}")
            return {"caption": "", "slides": []}
