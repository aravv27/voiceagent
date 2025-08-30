import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash-live-001")
    
    # Twilio (Required for outbound calls)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER")  # Your Twilio number
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    PUBLIC_DOMAIN: str = os.getenv("PUBLIC_DOMAIN", "your-domain.com")  # For webhooks
    
    # Audio
    TWILIO_SAMPLE_RATE: int = int(os.getenv("TWILIO_SAMPLE_RATE", "8000"))
    GEMINI_INPUT_RATE: int = int(os.getenv("GEMINI_INPUT_RATE", "16000"))
    GEMINI_OUTPUT_RATE: int = int(os.getenv("GEMINI_OUTPUT_RATE", "24000"))
    
    @classmethod
    def validate(cls):
        """Validate required environment variables for outbound calls"""
        required_fields = [
            ("GEMINI_API_KEY", cls.GEMINI_API_KEY),
            ("TWILIO_ACCOUNT_SID", cls.TWILIO_ACCOUNT_SID),
            ("TWILIO_AUTH_TOKEN", cls.TWILIO_AUTH_TOKEN),
            ("TWILIO_PHONE_NUMBER", cls.TWILIO_PHONE_NUMBER),
            ("PUBLIC_DOMAIN", cls.PUBLIC_DOMAIN)
        ]
        
        missing_fields = [field for field, value in required_fields if not value]
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
        
        return True

config = Config()
