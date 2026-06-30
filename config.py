import os

class Config:
    """Bot configuration settings"""
    
    # Get bot token from environment variable
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # OpenAI API Key (optional - for Whisper)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
    
    # Optional settings
    PORT = int(os.getenv('PORT', 8443))
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError(
                "BOT_TOKEN is not set. Please add it as an environment variable."
            )
        return True

Config.validate()
