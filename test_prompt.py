"""
Quick prompt tester — calls Gemini with a prompt and a photo, saves the result.

All files live in the testing/ folder:
    testing/prompt.txt       — the prompt (edit this)
    testing/<TEST_PHOTO>     — your test photo
    testing/result_1.png     — results auto-numbered
    testing/result_2.png
    ...

Usage: python test_prompt.py
"""

import sys
import os
import io

from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(__file__)
TESTING_DIR = os.path.join(BASE_DIR, "testing")

load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-3-pro-image-preview"

# ── Change this to switch test photo ──────────────────────────────────────────
TEST_PHOTO = "30.jpg"
# ──────────────────────────────────────────────────────────────────────────────

PROMPT_FILE = os.path.join(TESTING_DIR, "prompt.txt")


def next_result_path():
    """Return next available result_N.png path."""
    n = 1
    while True:
        path = os.path.join(TESTING_DIR, f"result_{n}.png")
        if not os.path.exists(path):
            return path
        n += 1


def main():
    photo_path = os.path.join(TESTING_DIR, TEST_PHOTO)

    if not os.path.exists(photo_path):
        print(f"Photo not found: {photo_path}")
        print(f"Drop your test photo into testing/ and set TEST_PHOTO at line 32.")
        sys.exit(1)
    if not os.path.exists(PROMPT_FILE):
        print(f"Prompt not found: {PROMPT_FILE}")
        sys.exit(1)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    print(f"Prompt: {PROMPT_FILE}")
    print(f"Photo:  {photo_path}")
    print(f"Model:  {GEMINI_MODEL}")
    print()

    image = Image.open(photo_path)
    # Resize to match Telegram compression (max 1280px on longest side)
    max_side = 1280
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.LANCZOS)
        print(f"Resized to: {image.size}")

    # Configure client (timeout will be set per-request)
    client = genai.Client(api_key=GEMINI_API_KEY)

    print("Calling Gemini...")
    print("(This may take several minutes for complex image generation...)")
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"],
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
                ],
            ),
        )
    except Exception as e:
        print(f"Error calling Gemini API: {type(e).__name__}: {e}")
        print(f"\nTroubleshooting tips:")
        print(f"  - Check your internet connection")
        print(f"  - Verify your API key in .env")
        print(f"  - Try again in a few moments (API might be temporarily down)")
        sys.exit(1)

    result_image = None
    result_text = None

    if not response.parts:
        print("Empty response from Gemini (possible content safety block).")
        if hasattr(response, 'prompt_feedback'):
            print(f"Feedback: {response.prompt_feedback}")
        sys.exit(1)

    for part in response.parts:
        if part.inline_data is not None:
            result_image = Image.open(io.BytesIO(part.inline_data.data))
        elif part.text is not None:
            result_text = part.text

    if result_image:
        output_path = next_result_path()
        result_image.save(output_path, format="PNG")
        print(f"Saved: {output_path}")
        if sys.platform == "darwin":
            os.system(f'open "{output_path}"')
    else:
        print("No image returned.")
        if result_text:
            print(f"Model response: {result_text}")


if __name__ == "__main__":
    main()
