import audioop
import base64
import numpy as np
import logging

logger = logging.getLogger(__name__)

class AudioConverter:
    def __init__(self):
        self.twilio_sample_rate = 8000  # Twilio uses 8kHz
        self.gemini_input_rate = 16000  # Gemini expects 16kHz
        self.gemini_output_rate = 24000  # Gemini outputs 24kHz
        
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
    
    def pcm_to_mulaw(self, pcm_data: bytes) -> bytes:
        """Convert PCM audio from Gemini to μ-law for Twilio"""
        try:
            # Resample from 24kHz to 8kHz for Twilio
            pcm_resampled = audioop.ratecv(
                pcm_data, 2, 1,
                self.gemini_output_rate,
                self.twilio_sample_rate,
                None
            )[0]
            
            # Convert linear PCM to μ-law
            mulaw_data = audioop.lin2ulaw(pcm_resampled, 2)
            
            return mulaw_data
            
        except Exception as e:
            logger.error(f"Error converting PCM to μ-law: {e}")
            return b""
