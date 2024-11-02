""" 

NOT READY YET, STILL WORKING ON IT.

⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠳⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣀⡴⢧⣀⠀⠀⣀⣠⠤⠤⠤⠤⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠘⠏⢀⡴⠊⠁⠀⠀⠀⠀⠀⠀⠈⠙⠦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣰⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢶⣶⣒⣶⠦⣤⣀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣰⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣟⠲⡌⠙⢦⠈⢧⠀
⠀⠀⠀⣠⢴⡾⢟⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡴⢃⡠⠋⣠⠋⠀
⠐⠀⠞⣱⠋⢰⠁⢿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⠤⢖⣋⡥⢖⣫⠔⠋⠀⠀⠀
⠈⠠⡀⠹⢤⣈⣙⠚⠶⠤⠤⠤⠴⠶⣒⣒⣚⣩⠭⢵⣒⣻⠭⢖⠏⠁⢀⣀⠀⠀⠀⠀
⠠⠀⠈⠓⠒⠦⠭⠭⠭⣭⠭⠭⠭⠭⠿⠓⠒⠛⠉⠉⠀⠀⣠⠏⠀⠀⠘⠞⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠓⢤⣀⠀⠀⠀⠀⠀⠀⣀⡤⠞⠁⠀⣰⣆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠘⠿⠀⠀⠀⠀⠀⠈⠉⠙⠒⠒⠛⠉⠁⠀⠀⠀⠉⢳⡞⠉⠀⠀⠀⠀⠀


"""

import os
import logging
from openai import OpenAI
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_audioclips, CompositeAudioClip
import pysrt
from typing import List
import json

from src.video_editor import VideoEditor
from src.captions.subtitle_generator import SubtitleGenerator
from moviepy.audio.fx.all import audio_fadein, audio_fadeout
from moviepy.video.fx.all import speedx


openai_api_key = os.getenv("OPENAI_API_KEY")


class TranslationEngine:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.video_editor = VideoEditor()
        self.subtitle_generator = SubtitleGenerator()

    async def translate_video(self, video_path, target_language):
        """
        Translate the video script and generate a new audio file.

        Args:
            video_path (str): Path to the original video file.
            target_language (str): The target language for translation.

        Returns:
            dict: A dictionary containing the status and the path to the translated video.
        """
        try:
            # Extract audio from the video
            video = VideoFileClip(video_path)
            audio = video.audio
            # Save audio path
            audio_path = os.path.join(self.base_dir, '..', '..', 'assets', 'extracted_audio.mp3')
            audio.write_audiofile(audio_path)

            # Generate subtitles from the audio
            subtitles_path = await self.subtitle_generator.generate_subtitles_for_translation(audio_path)

            translated_script = await self._translate_subtitles(subtitles_path, target_language)
            
            # Generate new audio for the translated script
            translated_audio_path = await self.generate_voice(translated_script)
            
            # Add translated audio to the video
            translated_video = self.video_editor.add_audio_to_video(
                video_path,
                translated_audio_path
            )

            # Generate a path for the output video
            output_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(output_dir, exist_ok=True)
            translated_video_path = os.path.join(output_dir, 'translated_video.mp4')

            logging.info(f"Rendering the translated video: {translated_video_path}")
            translated_video.write_videofile(translated_video_path, codec='libx264', audio_codec='aac')

            return {"status": "success", "translated_video_path": translated_video_path}

        except Exception as e:
            logging.error(f"Error in video translation: {e}")
            return {"status": "error", "message": f"Error in video translation: {str(e)}"}


    async def _translate_subtitles(self, subtitles_path: str, target_language: str) -> List[pysrt.SubRipItem]:
        """Translate each subtitle in the SRT file using OpenAI's API."""
        try:
            # Read subtitles from the file
            subs = pysrt.open(subtitles_path)
            
            translated_subs = []
            for i, sub in enumerate(subs):
                # Get previous and next subtitle texts
                prev_text = subs[i-1].text if i > 0 else ""
                next_text = subs[i+1].text if i < len(subs) - 1 else ""

                json_response = '''{
                    "current_translated_subtitle": ""
                }'''
                
                # Translate the text with context
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": f"You are a professional translator. Translate the current subtitle to {target_language}. Use the previous and next subtitles as context to ensure the translation is coherent. Answer in the JSON format: {json_response}"},
                        {"role": "user", "content": f"Previous subtitle: {prev_text}\nCurrent subtitle: {sub.text}\nNext subtitle: {next_text}"}
                    ]
                )
                response_json = response.choices[0].message.content
                
                # Parse the JSON response
                translated_sub_data = json.loads(response_json)
                translated_text = translated_sub_data.get("current_translated_subtitle", "")
                # Create a new SubRipItem with translated text
                translated_sub = pysrt.SubRipItem(
                    index=sub.index,
                    start=sub.start,
                    end=sub.end,
                    text=translated_text
                )
                translated_subs.append(translated_sub)
            
            return translated_subs
        except Exception as e:
            logging.error(f"Error translating subtitles: {e}")
            raise

    # Common function
    async def generate_voice(self, translated_subtitles):
        """Generate a new audio file for each translated subtitle line and match with timing."""
        try:
            speech_file_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(speech_file_dir, exist_ok=True)
            
            audio_clips = []
            
            for i, subtitle in enumerate(translated_subtitles):
                speech_file_path = os.path.join(speech_file_dir, f'generated_speech_{i}.mp3')
                response = self.openai_client.audio.speech.create(
                    model="tts-1",
                    voice="echo",
                    input=subtitle.text
                )
                response.stream_to_file(speech_file_path)
                
                # Load the generated audio
                audio_clip = AudioFileClip(speech_file_path)
                
                # Calculate the desired duration based on subtitle timing
                desired_duration = (subtitle.end.seconds + subtitle.end.milliseconds / 1000) - (subtitle.start.seconds + subtitle.start.milliseconds / 1000)
                
                # if audio duration is longer than desired duration, speed up the audio
                if audio_clip.duration > desired_duration:
                    speed_factor = audio_clip.duration / desired_duration
                    audio_clip = CompositeAudioClip([audio_clip]).set_duration(audio_clip.duration)
                    audio_clip = speedx(audio_clip, factor=speed_factor)
                # if audio duration is shorter than desired duration, slow down the audio
                elif audio_clip.duration < desired_duration:
                    speed_factor = desired_duration / audio_clip.duration
                    audio_clip = CompositeAudioClip([audio_clip]).set_duration(audio_clip.duration)
                    audio_clip = speedx(audio_clip, factor=speed_factor)

                # Ensure the audio clip duration matches the desired duration
                audio_clip = audio_clip.set_duration(desired_duration)

                # Set the start time for the audio clip
                audio_clip = audio_clip.set_start(subtitle.start.seconds + subtitle.start.milliseconds / 1000)
                
                audio_clips.append(audio_clip)
                
                # Remove the temporary audio file
                os.remove(speech_file_path)
            
            # Combine all audio clips
            final_audio = CompositeAudioClip(audio_clips)
            final_audio.fps = 44100
            
            # Export the full audio
            full_audio_path = os.path.join(speech_file_dir, 'full_generated_speech.mp3')
            final_audio.write_audiofile(full_audio_path)
            
            logging.info("Voice generated successfully for all subtitle lines.")
            return full_audio_path
        except Exception as e:
            logging.error(f"Error generating voice: {e}")
            raise




