import os
import uuid
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_voice(script):
    try:
        unique_id = uuid.uuid4()
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'audios')
        os.makedirs(assets_dir, exist_ok=True)
        speech_file_path = os.path.join(assets_dir, f"voice_{unique_id}.mp3")
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="echo",
            input=script
        )
        response.stream_to_file(speech_file_path)
        logging.info("Voice generated successfully.")
        return speech_file_path
    except Exception as e:
        logging.error(f"Error generating voice: {e}")
