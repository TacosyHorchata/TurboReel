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
import json  # Added import for JSON operations

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

class VideoEditor:
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

    # Create antoher class to handle ai generation
    async def generate_script(self, key_points, prompt_template):
        try:
            completion = self.openai.chat.completions.create(  # Async call to create chat completion
                model="gpt-3.5-turbo-0125",
                max_tokens=250,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": f"{prompt_template['system_prompt']}"},
                    {"role": "user", "content": f"{prompt_template['user_prompt']} {key_points}"}
                ]
            )
            logging.info("Script generated successfully.")

            response_content = completion.choices[0].message.content  # Access the message content correctly

            # Parse the response content as JSON
            response_json = json.loads(response_content)
            return response_json

        except json.JSONDecodeError as json_err:
            logging.error(f"Error decoding JSON: {json_err}")
            return {}  # Return an empty dictionary on JSON decode error
        except Exception as e:
            logging.error(f"Error generating script: {e}")  # Log the error message
            return {}  # Return an empty dictionary on error

    # Create antoher class to handle ai generation
    async def generate_voice(self, script):
        try:
            unique_id = uuid.uuid4()
            assets_dir = os.path.join(self.base_dir, '..', 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            speech_file_path = os.path.join(assets_dir, f"voice_{unique_id}.mp3")
            
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice="echo",
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

    def add_audio_to_video(self, video_path, audio_path) -> VideoFileClip:
        try:
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(str(audio_path))
            final_clip = video_clip.set_audio(audio_clip)
            
            logging.info("Audio added to video successfully.")
            return final_clip
        except Exception as e:
            logging.error(f"Error adding audio to video: {e}")
            return None
    
    def crop_video_9_16(self, video_clip: VideoFileClip) -> VideoFileClip:
        try:
            # Crop the video to TikTok format (9:16 aspect ratio)
            video_width, video_height = video_clip.size
            target_aspect_ratio = 9 / 16
            target_height = video_height
            target_width = int(target_height * target_aspect_ratio)

            if target_width < video_width:
                # Center crop horizontally
                cropped_clip = video_clip.crop(x_center=video_width / 2, width=target_width, height=target_height)
            else:
                # If the video is already narrower than 9:16, don't crop
                cropped_clip = video_clip

            logging.info("Video cropped successfully")
            return cropped_clip
        except Exception as e:
            logging.error(f"Error cropping video: {e}")
            return None

    def add_captions_to_video(self, video_clip, subtitles_clips:list) -> CompositeVideoClip:
        try:
            if video_clip is None:
                raise ValueError("video_clip is None")

            # Ensure subtitles_clips is a list
            if not isinstance(subtitles_clips, list):
                logging.warning("subtitles_clips is not a list. Converting to a list.")
                subtitles_clips = [subtitles_clips] if subtitles_clips else []

            # Combine the video and subtitle clips
            final_clip = CompositeVideoClip([video_clip] + subtitles_clips)
            logging.info("Captions added to video successfully.")
            return final_clip
        except Exception as e:
            logging.error(f"Error adding captions to video: {e}")
            return None

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
        
        return CompositeVideoClip(clips)

    def render_final_video(self, final_clip) -> str:
        """Render the final video with all components added."""
        unique_id = uuid.uuid4()
        result_dir = os.path.abspath(os.path.join(self.base_dir, '../result'))
        os.makedirs(result_dir, exist_ok=True)
        output_path = os.path.join(result_dir, f"final_video_{unique_id}.mp4")
        final_clip.write_videofile(output_path)
        logging.info("Final video rendered successfully.")
        return output_path
    
    def cleanup_files(self, file_paths, image_paths=None):
        """Delete temporary files and generated images to clean up the workspace."""
        # Clean up temporary files
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info(f"Deleted temporary file: {file_path}")
                else:
                    logging.warning(f"File not found: {file_path}")
            except Exception as e:
                logging.error(f"Error deleting file {file_path}: {e}")
        
        # Clean up generated images
        if image_paths:
            for image_path in image_paths:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logging.info(f"Deleted generated image: {image_path}")
                    else:
                        logging.warning(f"Image not found: {image_path}")
                except Exception as e:
                    logging.error(f"Error deleting image {image_path}: {e}")

    

## Pending stuff to do in this class:
# - Separate audio from captions in the add_audio_and_captions_to_video method
# - Render method separated from the add_images_to_video method
