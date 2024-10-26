import logging
import os
import pysrt
import uuid
from openai import OpenAI

from .utils import convert_seconds_to_srt_time

class SubtitleGenerator:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.convert_seconds_to_srt_time = convert_seconds_to_srt_time
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    async def generate_subtitles(self, audio_file: str):
        try:
            subtitles = await self.speech_to_text(audio_file)
            srt_file = pysrt.SubRipFile()

            for index, (start, end, text) in enumerate(subtitles):
                srt_file.append(pysrt.SubRipItem(index=index + 1, start=start, end=end, text=text))
            
            unique_id = uuid.uuid4()
            output_dir = os.path.join(self.base_dir, 'assets')
            output_file = os.path.join(output_dir, f'subtitles_{unique_id}.srt')
            srt_file.save(output_file)
            
            logging.info("Subtitles generated and saved successfully.")
            return output_file  # Return the path to the saved SRT file
        except Exception as e:
            logging.error(f"Error generating subtitles: {e}")
            return None

    async def speech_to_text(self, audio_file: str):
        try:
            audio_file = open(audio_file, "rb")  # Open the audio file
            transcript = self.openai.audio.transcriptions.create(  # Use OpenAI's transcription method
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
            subtitles = []
            current_words = []
            subtitle_start_time = None

            for i, word_info in enumerate(transcript.words):
                word_start_time = self.convert_seconds_to_srt_time(word_info.start)
                word_end_time = self.convert_seconds_to_srt_time(word_info.end)

                previous_word_end = self.convert_seconds_to_srt_time(transcript.words[i - 1].end)

                if subtitle_start_time is None:
                    subtitle_start_time = word_start_time

                current_words.append(word_info.word.strip())

                #check if current subtitle is long enough or if the next word is too long
                if len(current_words) >= 2 or (i > 0 and word_start_time.ordinal - previous_word_end.ordinal >= 600):
                    #formatted_text = " ".join(current_words[:1]) + "\n" + " ".join(current_words[1:])
                    formatted_text = " ".join(current_words)
                    subtitles.append((subtitle_start_time, word_end_time, formatted_text))
                    current_words = []
                    subtitle_start_time = None

            # Handle any remaining word
            if current_words:
                # Old multi-line approach (commented out)
                # formatted_text = " ".join(current_words[:1])
                # if len(current_words) > 1:
                #     formatted_text += "\n" + " ".join(current_words[1:])
                
                # New single-line approach
                formatted_text = " ".join(current_words)
                subtitles.append((subtitle_start_time, word_end_time, formatted_text))

            logging.info(f"Speech-to-text transcription completed.")
            return subtitles
        except Exception as e:
            logging.error(f"Error in speech-to-text transcription: {e}")
            return []

    async def generate_subtitles_for_translation(self, audio_file):
        try:
            subtitles = await self.speech_to_text_for_translation(audio_file)
            srt_file = pysrt.SubRipFile()

            for index, (start, end, text) in enumerate(subtitles):
                srt_file.append(pysrt.SubRipItem(index=index + 1, start=start, end=end, text=text))
            
            unique_id = uuid.uuid4()
            output_dir = os.path.join(self.base_dir, 'assets')
            output_file = os.path.join(output_dir, f'subtitles_{unique_id}.srt')
            srt_file.save(output_file)
            
            logging.info("Subtitles generated and saved successfully.")
            return output_file  # Return the path to the saved SRT file
        except Exception as e:
            logging.error(f"Error generating subtitles: {e}")
            return None

    async def speech_to_text_for_translation(self, audio_file):
        try:
            audio_file = open(audio_file, "rb")  # Open the audio file
            transcript = self.openai.audio.transcriptions.create(  # Use OpenAI's transcription method
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
            subtitles = []
            current_words = []
            subtitle_start_time = None

            for i, word_info in enumerate(transcript.words):
                word_start_time = self.convert_seconds_to_srt_time(word_info.start)
                word_end_time = self.convert_seconds_to_srt_time(word_info.end)

                previous_word_end = self.convert_seconds_to_srt_time(transcript.words[i - 1].end)

                if subtitle_start_time is None:
                    subtitle_start_time = word_start_time

                current_words.append(word_info.word.strip())

                #check if current subtitle is long enough or if the next word is too long
                if len(current_words) >= 8:
                    formatted_text = " ".join(current_words[:4]) + "\n" + " ".join(current_words[4:])
                    subtitles.append((subtitle_start_time, word_end_time, formatted_text))
                    current_words = []
                    subtitle_start_time = None

            # Handle any remaining word
            if current_words:
                formatted_text = " ".join(current_words[:4])
                if len(current_words) > 4:
                    formatted_text += "\n" + " ".join(current_words[4:])
                subtitles.append((subtitle_start_time, word_end_time, formatted_text))

            logging.info(f"Speech-to-text transcription completed.")
            return subtitles
        except Exception as e:
            logging.error(f"Error in speech-to-text transcription: {e}")
            return []
