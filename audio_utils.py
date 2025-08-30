# import audioop
# import base64
# import numpy as np
# import logging

# logger = logging.getLogger(__name__)

# class AudioConverter:
#     def __init__(self):
#         self.twilio_sample_rate = 8000  # Twilio uses 8kHz
#         self.gemini_input_rate = 16000  # Gemini expects 16kHz
#         self.gemini_output_rate = 24000  # Gemini outputs 24kHz
        
#     def mulaw_to_pcm(self, mulaw_data: str) -> bytes:
#         """Convert μ-law encoded audio from Twilio to PCM for Gemini"""
#         try:
#             # Decode base64
#             mulaw_bytes = base64.b64decode(mulaw_data)
            
#             # Convert μ-law to linear PCM (16-bit)
#             pcm_data = audioop.ulaw2lin(mulaw_bytes, 2)
            
#             # Resample from 8kHz to 16kHz for Gemini
#             pcm_resampled = audioop.ratecv(
#                 pcm_data, 2, 1, 
#                 self.twilio_sample_rate, 
#                 self.gemini_input_rate, 
#                 None
#             )[0]
            
#             return pcm_resampled
            
#         except Exception as e:
#             logger.error(f"Error converting μ-law to PCM: {e}")
#             return b""
    
#     def pcm_to_mulaw(self, pcm_data: bytes) -> bytes:
#         """Convert PCM audio from TTS (24kHz) to μ-law for Twilio (8kHz)"""
#         try:
#             # TTS generates at various rates, resample to 8kHz for Twilio
#             pcm_resampled = audioop.ratecv(
#                 pcm_data, 2, 1,
#                 24000,  # TTS output rate (pyttsx3 typically 22050 or 24000)
#                 self.twilio_sample_rate,  # 8000 Hz for Twilio
#                 None
#             )[0]
            
#             # Convert linear PCM to μ-law
#             mulaw_data = audioop.lin2ulaw(pcm_resampled, 2)
            
#             return mulaw_data
            
#         except Exception as e:
#             logger.error(f"Error converting PCM to μ-law: {e}")
#             return b""
    
#     # def pcm_to_mulaw(self, pcm_data: bytes) -> bytes:
#     #     """Convert PCM audio from Gemini to μ-law for Twilio"""
#     #     try:
#     #         # Resample from 24kHz to 8kHz for Twilio
#     #         pcm_resampled = audioop.ratecv(
#     #             pcm_data, 2, 1,
#     #             self.gemini_output_rate,
#     #             self.twilio_sample_rate,
#     #             None
#     #         )[0]
            
#     #         # Convert linear PCM to μ-law
#     #         mulaw_data = audioop.lin2ulaw(pcm_resampled, 2)
            
#     #         return mulaw_data
            
#     #     except Exception as e:
#     #         logger.error(f"Error converting PCM to μ-law: {e}")
#     #         return b""
from time import time
import audioop
import base64
import wave
import io
import logging
import traceback
logger = logging.getLogger(__name__)

class AudioConverter:
    def __init__(self):
        self.twilio_sample_rate = 8000  # Twilio uses 8kHz
        self.gemini_input_rate = 16000  # Gemini expects 16kHz
        
    def mulaw_to_pcm(self, mulaw_data: str) -> bytes:
        """Convert μ-law encoded audio from Twilio to PCM for Gemini"""
        try:
            # Decode base64
            mulaw_bytes = base64.b64decode(mulaw_data)
            
            # Convert μ-law to linear PCM (16-bit)
            pcm_data = audioop.ulaw2lin(mulaw_bytes, 2)
            
            # Resample from 8kHz to 16kHz for Gemini
            pcm_resampled = audioop.ratecv(
                pcm_data, 2, 1, 
                self.twilio_sample_rate, 
                self.gemini_input_rate, 
                None
            )[0]
            
            return pcm_resampled
            
        except Exception as e:
            logger.error(f"Error converting μ-law to PCM: {e}")
            return b""
    
    def wav_to_mulaw_chunks(self, wav_data: bytes) -> list:
        """Convert WAV file data to μ-law chunks for Twilio streaming"""
        try:
            # Save raw WAV for debugging
            debug_file = f"debug_tts_{int(time.time())}.wav"
            with open(debug_file, 'wb') as f:
                f.write(wav_data)
            logger.info(f"[DEBUG] 💾 Saved debug WAV file: {debug_file}")
            
            # Parse WAV and convert as before...
            with io.BytesIO(wav_data) as wav_stream:
                with wave.open(wav_stream, 'rb') as wav_file:
                    sample_rate = wav_file.getframerate()
                    sample_width = wav_file.getsampwidth()
                    channels = wav_file.getnchannels()
                    frames = wav_file.getnframes()
                    duration = frames / sample_rate
                    
                    logger.info(f"[DEBUG] 🎵 WAV Analysis:")
                    logger.info(f"[DEBUG] 🎵   Sample Rate: {sample_rate}Hz")
                    logger.info(f"[DEBUG] 🎵   Bit Depth: {sample_width*8}bit")
                    logger.info(f"[DEBUG] 🎵   Channels: {channels}")
                    logger.info(f"[DEBUG] 🎵   Duration: {duration:.2f}s")
                    logger.info(f"[DEBUG] 🎵   Total Frames: {frames}")
                    
                    pcm_data = wav_file.readframes(frames)
                    logger.info(f"[DEBUG] 🎵   PCM Data: {len(pcm_data)} bytes")
            
            # Rest of conversion...
            
        except Exception as e:
            logger.error(f"Error converting WAV to μ-law chunks: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    
    def pcm_to_mulaw(self, pcm_data: bytes, source_rate: int = 24000) -> bytes:
        """Convert raw PCM to μ-law for Twilio (legacy method for compatibility)"""
        try:
            # Resample to 8kHz for Twilio
            pcm_resampled = audioop.ratecv(
                pcm_data, 2, 1,
                source_rate,  # Source rate (passed as parameter)
                self.twilio_sample_rate,  # 8000 Hz for Twilio
                None
            )[0]
            
            # Convert linear PCM to μ-law
            mulaw_data = audioop.lin2ulaw(pcm_resampled, 2)
            
            return mulaw_data
            
        except Exception as e:
            logger.error(f"Error converting PCM to μ-law: {e}")
            return b""
