import os
from dotenv import load_dotenv  # <-- Add this line

# Load from .env file in current directory
load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash-live-001"
CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
        )
    )
)

async def test_conn():
    async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
        print("✅ Gemini Live connection established!")

import asyncio
asyncio.run(test_conn())
