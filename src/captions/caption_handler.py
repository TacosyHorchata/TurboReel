import os
import logging

from .subtitle_generator import SubtitleGenerator
from .video_captioner import VideoCaptioner

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)


class CaptionHandler:
    def __init__(self):
        self.subtitle_generator = SubtitleGenerator()
        self.video_captioner = VideoCaptioner()
        self.default_font = "Dacherry.ttf"

    async def process(self, audio_file: str, captions_color="white", shadow_color="cyan", font_size=60, font=None, width=540):
        subtitles_file = await self.subtitle_generator.generate_subtitles(audio_file)
        caption_clips = self.video_captioner.generate_captions_to_video(
            subtitles_file,
            font=font,
            captions_color=captions_color,
            shadow_color=shadow_color,
            font_size=font_size,
            width=width
        )
        return subtitles_file, caption_clips