# from dotenv import load_dotenv
# load_dotenv()

# import asyncio
# import json
# import base64
# import traceback
# from typing import Optional
# from fastapi import WebSocket
# import logging

# from google import genai
# from google.genai import types
# from audio_utils import AudioConverter
# from config import config

# logger = logging.getLogger(__name__)

# # Enterprise Gemini Live Configuration
# MODEL = config.GEMINI_MODEL  # e.g. "models/gemini-2.0-flash-live-001"
# client = genai.Client(
#     http_options={"api_version": "v1beta"},
#     api_key=config.GEMINI_API_KEY,
# )

# CONFIG = types.LiveConnectConfig(
#     response_modalities=["AUDIO"],
#     speech_config=types.SpeechConfig(
#         language_code="en-US",
#         voice_config=types.VoiceConfig(
#             prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
#         )
#     )
# )

# class TwilioGeminiAgent:
#     def __init__(self, websocket: WebSocket, call_sid: str):
#         self.websocket = websocket
#         self.call_sid = call_sid
#         self.session = None
#         self.audio_converter = AudioConverter()
#         self.running = False
#         self.ready = False
#         self.startup_complete = asyncio.Event()
#         self.audio_in_queue = asyncio.Queue()
#         self.audio_out_queue = asyncio.Queue(maxsize=50)
#         self.tasks = []
        
#         logger.info(f"[DEBUG] 🏗️ Agent initialized for call: {self.call_sid}")

#     async def stop(self):
#         """Stop the agent and cleanup resources"""
#         logger.info(f"[DEBUG] 🛑 Stopping agent for call: {self.call_sid}")
#         self.running = False
#         self.ready = False
        
#         # Cancel all tasks
#         for task in self.tasks:
#             if not task.done():
#                 task.cancel()
        
#         if self.tasks:
#             await asyncio.gather(*self.tasks, return_exceptions=True)
        
#         logger.info(f"[DEBUG] ✅ Agent stopped for call: {self.call_sid}")

#     async def start_and_wait(self):
#         """Start the agent and wait for it to be ready"""
#         logger.info(f"[DEBUG] 🚀 Starting agent for call: {self.call_sid}")
        
#         self.run_task = asyncio.create_task(self.run())
        
#         try:
#             await asyncio.wait_for(self.startup_complete.wait(), timeout=15.0)
#             logger.info(f"[DEBUG] ✅ Agent ready for call: {self.call_sid}")
#         except asyncio.TimeoutError:
#             logger.error(f"[DEBUG] ⏰ Agent startup timeout for call: {self.call_sid}")
#             await self.stop()
#             raise Exception("Gemini agent startup timeout")

#     async def handle_incoming_audio(self, media_data: dict):
#         """Handle incoming audio from Twilio"""
#         try:
#             if not (self.running and self.ready and self.session):
#                 logger.debug(f"[DEBUG] ⏸️ Skipping audio - Agent not ready")
#                 return
                
#             payload = media_data.get("payload", "")
#             if not payload:
#                 return
                
#             # Convert μ-law to PCM and upsample to 16kHz
#             pcm_data = self.audio_converter.mulaw_to_pcm(payload)
            
#             # Queue for sending to Gemini
#             try:
#                 self.audio_out_queue.put_nowait({
#                     "data": pcm_data,
#                     "mime_type": "audio/pcm"
#                 })
#             except asyncio.QueueFull:
#                 logger.warning(f"[DEBUG] 📦 Audio queue full, dropping packet")
                
#         except Exception as e:
#             logger.error(f"[DEBUG] ❌ Audio handling error: {e}")

#     async def send_audio_to_twilio(self, audio_data: bytes):
#         """Send audio back to Twilio via WebSocket"""
#         try:
#             # Convert PCM from Gemini to μ-law for Twilio
#             mulaw_data = self.audio_converter.pcm_to_mulaw(audio_data)
            
#             message = {
#                 "event": "media",
#                 "streamSid": self.call_sid,
#                 "media": {
#                     "payload": base64.b64encode(mulaw_data).decode('utf-8')
#                 }
#             }
            
#             await self.websocket.send_text(json.dumps(message))
#             logger.debug(f"[DEBUG] 🔊 Audio sent to Twilio for call: {self.call_sid}")
            
#         except Exception as e:
#             logger.error(f"[DEBUG] ❌ Error sending audio to Twilio: {e}")

#     async def send_to_gemini(self):
#         """Send audio from queue to Gemini"""
#         logger.info(f"[DEBUG] 📤 Started Gemini sender for call: {self.call_sid}")
        
#         while self.running:
#             try:
#                 msg = await self.audio_out_queue.get()
#                 await self.session.send(input=msg)
#                 logger.debug(f"[DEBUG] 📨 Audio sent to Gemini")
#             except Exception as e:
#                 logger.error(f"[DEBUG] ❌ Gemini send error: {e}")
#                 if self.running:
#                     await asyncio.sleep(0.5)

#     async def receive_from_gemini(self):
#         """Receive responses from Gemini"""
#         logger.info(f"[DEBUG] 👂 Started Gemini receiver for call: {self.call_sid}")
        
#         while self.running:
#             try:
#                 turn = self.session.receive()
#                 async for response in turn:
#                     if not self.running:
#                         break
                        
#                     if data := response.data:
#                         logger.info(f"[DEBUG] 🔊 Gemini sent audio: {len(data)} bytes")
#                         await self.send_audio_to_twilio(data)
                        
#                     if text := response.text:
#                         logger.info(f"[DEBUG] 🤖 Gemini transcript: {text}")
                        
#             except Exception as e:
#                 logger.error(f"[DEBUG] ❌ Gemini receive error: {e}")
#                 if self.running:
#                     await asyncio.sleep(1)
                    
#         logger.info(f"[DEBUG] 🔇 Gemini receiver stopped for call: {self.call_sid}")

#     async def run(self):
#         """Main agent loop - connects to Gemini and manages audio streaming"""
#         try:
#             logger.info(f"[DEBUG] 🔌 Connecting to Gemini for call: {self.call_sid}")
#             self.running = True
            
#             async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
#                 self.session = session
#                 logger.info(f"[DEBUG] ✅ Gemini session established for call: {self.call_sid}")
                
#                 # Send initial greeting
#                 await self.session.send(input="Hello! I'm your AI assistant. I'm ready to talk with you. Please speak when you're ready.")
#                 logger.info(f"[DEBUG] 👋 Initial greeting sent to Gemini")
                
#                 # Mark as ready
#                 self.ready = True
#                 self.startup_complete.set()
                
#                 # Start audio processing tasks
#                 self.tasks = [
#                     asyncio.create_task(self.receive_from_gemini()),
#                     asyncio.create_task(self.send_to_gemini())
#                 ]
                
#                 logger.info(f"[DEBUG] 🏃 Processing tasks started for call: {self.call_sid}")
                
#                 # Wait for tasks to complete
#                 await asyncio.gather(*self.tasks, return_exceptions=True)
                
#         except Exception as e:
#             logger.error(f"[DEBUG] ❌ Gemini connection error: {e}")
#             logger.error(traceback.format_exc())
#         finally:
#             self.running = False
#             self.ready = False
#             logger.info(f"[DEBUG] 🏁 Agent run completed for call: {self.call_sid}")

from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import base64
import traceback
import tempfile
import os
from typing import Optional
from fastapi import WebSocket
import logging
import pyttsx3
from gtts import gTTS
import pygame
import io
import wave

from audio_utils import AudioConverter
from config import config

logger = logging.getLogger(__name__)

class TwilioTTSAgent:
    def __init__(self, websocket: WebSocket, call_sid: str):
        self.websocket = websocket
        self.call_sid = call_sid
        self.audio_converter = AudioConverter()
        self.running = False
        self.ready = False
        self.startup_complete = asyncio.Event()
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue(maxsize=50)
        self.tasks = []
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # Speed
        self.tts_engine.setProperty('volume', 0.9)  # Volume
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
        
        logger.info(f"[DEBUG] 🏗️ TTS Agent initialized for call: {self.call_sid}")

    async def stop(self):
        """Stop the agent and cleanup resources"""
        logger.info(f"[DEBUG] 🛑 Stopping TTS agent for call: {self.call_sid}")
        self.running = False
        self.ready = False
        
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        pygame.mixer.quit()
        logger.info(f"[DEBUG] ✅ TTS Agent stopped for call: {self.call_sid}")

    async def start_and_wait(self):
        """Start the agent and wait for it to be ready"""
        logger.info(f"[DEBUG] 🚀 Starting TTS agent for call: {self.call_sid}")
        
        self.run_task = asyncio.create_task(self.run())
        
        try:
            await asyncio.wait_for(self.startup_complete.wait(), timeout=15.0)
            logger.info(f"[DEBUG] ✅ TTS Agent ready for call: {self.call_sid}")
        except asyncio.TimeoutError:
            logger.error(f"[DEBUG] ⏰ TTS Agent startup timeout for call: {self.call_sid}")
            await self.stop()
            raise Exception("TTS agent startup timeout")

    async def handle_incoming_audio(self, media_data: dict):
        """Handle incoming audio from Twilio - convert to text (mock)"""
        try:
            if not (self.running and self.ready):
                logger.debug(f"[DEBUG] ⏸️ Skipping audio - Agent not ready")
                return
                
            payload = media_data.get("payload", "")
            if not payload:
                return
                
            # For demo, we'll simulate speech recognition
            # In production, you'd use speech-to-text here
            logger.info(f"[DEBUG] 🎤 Received audio, simulating speech recognition...")
            
            # Mock responses based on time or simple patterns
            responses = [
                "Hello! How can I help you today?",
                "That's interesting! Tell me more.",
                "I understand. Is there anything else I can assist you with?",
                "Thank you for calling. Have a great day!",
                "I'm here to help you with any questions."
            ]
            
            import random
            response_text = random.choice(responses)
            
            # Queue response for TTS
            await self.audio_out_queue.put(response_text)
                
        except Exception as e:
            logger.error(f"[DEBUG] ❌ Audio handling error: {e}")

    async def text_to_speech_async(self, text: str) -> bytes:
        """Convert text to speech and return audio bytes"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech with pyttsx3
            await asyncio.to_thread(self.tts_engine.save_to_file, text, temp_path)
            await asyncio.to_thread(self.tts_engine.runAndWait)
            
            # Read the generated audio file
            with open(temp_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            logger.info(f"[DEBUG] 🔊 Generated {len(audio_data)} bytes of TTS audio")
            return audio_data
            
        except Exception as e:
            logger.error(f"[DEBUG] ❌ TTS generation error: {e}")
            return b""

    async def stream_audio_to_twilio(self, audio_data: bytes):
        """Stream audio data to Twilio in proper chunks"""
        try:
            # Convert WAV to μ-law chunks
            chunks = self.audio_converter.wav_to_mulaw_chunks(audio_data)
            
            if not chunks:
                logger.warning(f"[DEBUG] No audio chunks generated")
                return
            
            logger.info(f"[DEBUG] Streaming {len(chunks)} chunks to Twilio")
            
            # Stream each chunk with proper timing
            for i, chunk in enumerate(chunks):
                message = {
                    "event": "media",
                    "streamSid": self.call_sid,
                    "media": {
                        "payload": base64.b64encode(chunk).decode('utf-8')
                    }
                }
                
                await self.websocket.send_text(json.dumps(message))
                await asyncio.sleep(0.02)  # 20ms per chunk
                
                if i % 50 == 0:  # Log every second
                    logger.debug(f"[DEBUG] Sent chunk {i+1}/{len(chunks)}")
                    
            logger.info(f"[DEBUG] ✅ Completed streaming {len(chunks)} chunks to Twilio")
            
        except Exception as e:
            logger.error(f"[DEBUG] ❌ Error streaming audio to Twilio: {e}")



    async def process_tts_queue(self):
        """Process TTS requests from queue"""
        logger.info(f"[DEBUG] 🔊 Started TTS processor for call: {self.call_sid}")
        
        while self.running:
            try:
                # Get text to convert
                text = await self.audio_out_queue.get()
                logger.info(f"[DEBUG] 🗣️ Converting to speech: {text[:50]}...")
                
                # Convert to speech
                audio_data = await self.text_to_speech_async(text)
                
                if audio_data:
                    # Stream to Twilio
                    await self.stream_audio_to_twilio(audio_data)
                    logger.info(f"[DEBUG] ✅ TTS response sent to call: {self.call_sid}")
                
            except Exception as e:
                logger.error(f"[DEBUG] ❌ TTS processing error: {e}")
                if self.running:
                    await asyncio.sleep(0.5)
                    
        logger.info(f"[DEBUG] 🔇 TTS processor stopped for call: {self.call_sid}")

    async def run(self):
        """Main agent loop"""
        try:
            logger.info(f"[DEBUG] 🔌 Starting TTS agent for call: {self.call_sid}")
            self.running = True
            
            # Send initial greeting
            await asyncio.sleep(1)
            await self.audio_out_queue.put("Hello! I'm your AI assistant. How can I help you today?")
            
            # Mark as ready
            self.ready = True
            self.startup_complete.set()
            
            # Start processing task
            self.tasks = [
                asyncio.create_task(self.process_tts_queue())
            ]
            
            logger.info(f"[DEBUG] 🏃 TTS processing started for call: {self.call_sid}")
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"[DEBUG] ❌ TTS agent error: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.running = False
            self.ready = False
            logger.info(f"[DEBUG] 🏁 TTS agent run completed for call: {self.call_sid}")

# For compatibility with existing code, create alias
TwilioGeminiAgent = TwilioTTSAgent
