# gemini_helper.py
import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY not found")

genai.configure(api_key=api_key)

# MOST RELIABLE vision model as of Dec 28, 2025 (avoids empty response bug in 2.5 series)
MODEL_NAME = "gemini-2.0-flash"  # Stable, consistent vision output

_vision_model = genai.GenerativeModel(
    MODEL_NAME,
    generation_config=genai.GenerationConfig(
        temperature=0.1,
        max_output_tokens=1024,
    )
)

def get_vision_model():
    return _vision_model

def analyze_image_with_prompt(
    image_path: str,
    prompt: str,
    temperature: float = 0.1
) -> Optional[str]:
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return None

    try:
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        response = get_vision_model().generate_content(
            [prompt, img],
            generation_config=genai.GenerationConfig(temperature=temperature)
        )

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            print(f"Blocked: {response.prompt_feedback.block_reason}")
            return None

        if response.parts:
            text = "".join(part.text for part in response.parts if hasattr(part, "text"))
            return text.strip()

        print("No text in response parts.")
        return None

    except Exception as e:
        print(f"Gemini error: {e}")
        return None