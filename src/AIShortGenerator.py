import os
import logging
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip
from openai import OpenAI
import pysrt
from yt_dlp import YoutubeDL
from pathlib import Path
import uuid
import re  # Added import for regular expression operations

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

class AIShortGenerator:
    def __init__(self, openai_api_key):
        self.openai = OpenAI(api_key=openai_api_key)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def download_video(self, youtube_url):
        try:
            downloads_dir = os.path.join(self.base_dir, '..', 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio',
                'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
                info_dict = ydl.extract_info(youtube_url, download=False)
                video_path = ydl.prepare_filename(info_dict)
                # Ensure the video path is in mp4 format
                if not video_path.endswith('.mp4'):
                    video_path = video_path.rsplit('.', 1)[0] + '.mp4'

            logging.info("Video downloaded successfully.")
            return video_path
        except Exception as e:
            logging.error(f"Error downloading video: {e}")
            return None

    def cut_video(self, video_path, start_time, end_time):
        if not os.path.exists(video_path):
            logging.error(f"Video file does not exist, {video_path}")
            return
        try:
            unique_id = uuid.uuid4()
            assets_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            output_path = os.path.join(assets_dir, f"cut_video_{unique_id}.mp4")
            
            clip = VideoFileClip(video_path)
            cut_clip = clip.subclip(start_time, end_time)
            cut_clip.write_videofile(output_path)
            logging.info("Video cut successfully.")
            return output_path
        except Exception as e:
            logging.error(f"Error cutting video: {e}")

    async def generate_script(self, key_points, prompt_template):
        try:
            completion = self.openai.chat.completions.create(  # Async call to create chat completion
                model="gpt-3.5-turbo-0125",
                max_tokens=250,
                messages=[
                    {"role": "system", "content": f"{prompt_template['system_prompt']}"},
                    {"role": "user", "content": f"{prompt_template['user_prompt']} {key_points}"}
                ]
            )
            logging.info("Script generated successfully.")

            response = completion.choices[0].message.content  # Access the message content correctly
            response = re.sub(r"(?i)Reddit question", "", response)  # Case-insensitive replacement
            response = re.sub(r"(?i)Youtube short story", "", response)  # Case-insensitive replacement
            return response

        except Exception as e:
            logging.error(f"Error generating script: {e}")  # Log the error message
            return ""  # Return an empty string on error

    def generate_subtitles(self, audio_file):
        try:
            subtitles = self.speech_to_text(audio_file)
            srt_file = pysrt.SubRipFile()

            for index, (start, end, text) in enumerate(subtitles):
                srt_file.append(pysrt.SubRipItem(index=index + 1, start=start, end=end, text=text))
            
            unique_id = uuid.uuid4()
            assets_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            srt_path = os.path.join(assets_dir, f'subtitles_{unique_id}.srt')
            srt_file.save(srt_path)
            logging.info("Subtitles generated and saved successfully.")
            return srt_path
        except Exception as e:
            logging.error(f"Error generating subtitles: {e}")

    def speech_to_text(self, audio_file):
        try:
            audio_file = open(audio_file, "rb")  # Open the audio file
            transcript = self.openai.audio.transcriptions.create(  # Use OpenAI's transcription method
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
            subtitles = []
            for word_info in transcript.words:  # Iterate through the words in the transcript
                start_time = self.convert_seconds_to_srt_time(word_info.start)  # Convert start time
                end_time = self.convert_seconds_to_srt_time(word_info.end)  # Convert end time
                text = word_info.word.strip()  # Get the word text
                subtitles.append((start_time, end_time, text))

            logging.info("Speech-to-text transcription completed.")
            return subtitles
        except Exception as e:
            logging.error(f"Error in speech-to-text transcription: {e}")
            return []

    def convert_seconds_to_srt_time(self, seconds):
        """Convert seconds into SubRipTime for SRT formatting"""
        millis = int((seconds % 1) * 1000)
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        return pysrt.SubRipTime(hours, mins, secs, millis)

    async def generate_voice(self, script):
        try:
            unique_id = uuid.uuid4()
            assets_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            speech_file_path = os.path.join(assets_dir, f"voice_{unique_id}.mp3")
            
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=script
            )
            response.stream_to_file(speech_file_path)
            logging.info("Voice generated successfully.")
            return speech_file_path
        except Exception as e:
            logging.error(f"Error generating voice: {e}")

    def load_subtitles(self, subtitles_path):
        try:
            return pysrt.open(subtitles_path)  # Return the loaded SRT file with start and end times
        except Exception as e:
            logging.error(f"Error loading subtitles: {e}")
            return []  # Return empty list on failure

    def add_audio_and_captions_to_video(self, video_path, audio_path, subtitles_path):
        try:
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(str(audio_path))
            final_clip = video_clip.set_audio(audio_clip)
            # Load subtitles from the SRT file
            subtitles = self.load_subtitles(subtitles_path)
            # Create annotated clips based on the loaded subtitles
            annotated_clips = [
                TextClip(sub.text, fontsize=42, color='white', font='Arial')  # Added stroke color and width for better contrast
                .set_position('center')
                .set_start(sub.start.ordinal / 1000)  # Convert to seconds
                .set_duration((sub.end.ordinal - sub.start.ordinal) / 1000)  # Set duration in seconds
                for sub in subtitles if sub.start is not None and sub.end is not None
            ]

            # Crop the video to TikTok format (9:16 aspect ratio)
            video_width, video_height = video_clip.size
            target_aspect_ratio = 9 / 16
            target_height = video_height
            target_width = int(target_height * target_aspect_ratio)

            if target_width < video_width:
                # Center crop horizontally
                final_clip = final_clip.crop(x_center=video_width / 2, width=target_width, height=target_height)

            # Combine the video and subtitle clips
            final_clip = CompositeVideoClip([final_clip] + annotated_clips)
            #final_clip.write_videofile("result/final_video.mp4")  # Save the final video
            logging.info("Audio and subtitles added to video successfully.")
            return final_clip
        except Exception as e:
            logging.error(f"Error adding audio and subtitles to video: {e}")

    def add_images_to_video(self, video_clip, images):
        """Add images to the video at specified intervals throughout the entire video duration."""
        clips = [video_clip]
        image_duration = 5  # Display each image for 5 seconds
        video_duration = video_clip.duration
        
        for i, image_path in enumerate(images):
            if image_path is not None:
                try:
                    image_clip = ImageClip(image_path).set_duration(image_duration)
                    image_clip = image_clip.set_position(('center', 70)).resize(height=video_clip.h / 3)
                    
                    # Calculate start time for each image
                    start_time = i * image_duration
                    
                    # If the image would extend beyond the video duration, adjust its duration
                    if start_time + image_duration > video_duration:
                        image_clip = image_clip.set_duration(video_duration - start_time)
                    
                    clips.append(image_clip.set_start(start_time))
                except Exception as e:
                    logging.error(f"Error processing image_path: {image_path}, {e}")
            # If image_path is None, we simply don't add an image for this interval
        
        final_clip = CompositeVideoClip(clips)
        unique_id = uuid.uuid4()
        result_dir = os.path.abspath(os.path.join(self.base_dir, '../result'))
        os.makedirs(result_dir, exist_ok=True)
        output_path = os.path.join(result_dir, f"final_video_with_images_{unique_id}.mp4")
        final_clip.write_videofile(output_path)
        logging.info("Final video with images created successfully.")
        return output_path
