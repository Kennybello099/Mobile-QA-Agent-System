import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=api_key)

def get_vision_model(model_name='models/gemini-pro-latest'):
    return genai.GenerativeModel(model_name)

def analyze_image_with_prompt(image_path, prompt):
    """Send an image and a prompt to Gemini and return the response."""
    model = get_vision_model()
    img = Image.open(image_path)

    response = model.generate_content([
        {"text": prompt},
        img
    ])

    # Safely extract text
    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    return "No response text found."