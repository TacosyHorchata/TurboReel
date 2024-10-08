import os
import logging
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip
from openai import OpenAI
import whisper
import pysrt
from yt_dlp import YoutubeDL
from pathlib import Path
import random
import yaml

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

from ImageHandler import ImageHandler

def load_config(file_path):
    """Load the YAML configuration file."""
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def load_prompt(file_path):
    """Load the YAML prompt template file."""
    with open(file_path, 'r') as file:
        prompt_template_file = yaml.safe_load(file)
    return prompt_template_file

class AIShortGenerator:
    def __init__(self, openai_api_key):
        self.openai = OpenAI(api_key=openai_api_key)

    def download_video(self, youtube_url):
        try:
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
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
            return video_path  # Return the path of the downloaded video
        except Exception as e:
            logging.error(f"Error downloading video: {e}")  # Log the error message
            return None  # Ensure to return None on error

    def cut_video(self, video_path, start_time, end_time):
        if not os.path.exists(video_path):
            logging.error(f"Video file does not exist, {video_path}")
            return
        try:
            clip = VideoFileClip(video_path)
            cut_clip = clip.subclip(start_time, end_time)
            cut_clip.write_videofile("assets/cut_video.mp4")
            logging.info("Video cut successfully.")
            return "assets/cut_video.mp4"  # Return the path of the cut video
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
            return completion.choices[0].message.content  # Access the message content correctly
        except Exception as e:
            logging.error(f"Error generating script: {e}")  # Log the error message
            return ""  # Return an empty string on error

    def generate_subtitles(self, audio_file):
        try:
            subtitles = self.speech_to_text(audio_file)  # Get the subtitles from speech_to_text
            srt_file = pysrt.SubRipFile()

            for index, (start, end, text) in enumerate(subtitles):
                srt_file.append(pysrt.SubRipItem(index=index + 1, start=start, end=end, text=text))

            srt_file.save('assets/subtitles.srt')  # Save as .srt
            logging.info("Subtitles generated and saved successfully.")
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
            speech_file_path = Path(__file__).parent / "assets/voice.mp3"  # Define the path for the output file
            response = self.openai.audio.speech.create(  # Create speech using the OpenAI API
                model="tts-1",
                voice="nova",  # Adjust the voice as needed
                input=script  # Use 'input' to provide the script
            )
            response.stream_to_file(speech_file_path)  # Stream the response to the specified file path
            logging.info("Voice generated successfully.")
            return speech_file_path  # Return the path of the generated audio
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
        """Add images to the video at specified intervals."""
        clips = [video_clip]
        start_interval = 5 # Display each image for 5 seconds
        for i, image_path in enumerate(images):
            image_clip = ImageClip(image_path).set_duration(start_interval)  
            image_clip = image_clip.set_position(('center', 70)).resize(height=video_clip.h / 3)  # Resize to fit video height
            clips.append(image_clip.set_start(i * start_interval))  # Start each image clip at intervals

        final_clip = CompositeVideoClip(clips)
        final_clip.write_videofile("result/final_video_with_images.mp4")  # Save the final video with images
        logging.info("Eureka!!!")

async def main():

    config = load_config('config.yaml')
    prompt_template = load_prompt('prompt_templates/reddit_thread.yaml')

    # Accessing configuration values
    openai_api_key = config['api_keys']['OPENAI_API_KEY']
    pexels_api_key = config['api_keys']['PEXELS_API_KEY']
    youtube_url = config['assets']['YOUTUBE_URL']
    video_topic = config['video_parameters']['VIDEO_TOPIC']

    logging.info(f"Starting TurboReelGPT video generation process for topic: {video_topic}")  # Log the start of the process
    ai_short_gen = AIShortGenerator(openai_api_key)  # Use getenv for safer access to environment variables
    image_handler = ImageHandler(pexels_api_key, openai_api_key)
    video_path = ai_short_gen.download_video(youtube_url)
    if video_path:
        logging.info(f"Video downloaded: {video_path}")  # Log the downloaded video path
        script = await ai_short_gen.generate_script(video_topic, prompt_template)
        if script:
            logging.info("Script generated successfully.")  # Log successful script generation
            audio_path = await ai_short_gen.generate_voice(script)  # Store the generated audio path
            if audio_path:  # Check if audio generation was successful
                # Get the audio length
                audio_clip = AudioFileClip(str(audio_path))
                audio_length = audio_clip.duration  # Get the duration of the audio in seconds
                audio_clip.close()  # Close the audio clip to free resources
                video_length = VideoFileClip(video_path).duration
                
                max_start_time = video_length - audio_length
                start_time = random.uniform(0, max_start_time)
                end_time = start_time + audio_length  # Use video_length instead of video

                # Calculate the maximum start time
                if max_start_time > 0:
                    cut_video_path = ai_short_gen.cut_video(video_path, start_time, end_time)  # Use random start time
                    if cut_video_path:
                        logging.info(f"Video cut successfully: {cut_video_path}")
                         # Generate subtitles for the audio
                        ai_short_gen.generate_subtitles(audio_path)  # Generate subtitles
                        logging.info(f"Subtitles generated successfully")
                        image_paths = image_handler.get_images_from_subtitles("assets/subtitles.srt", f"reddit thread about {video_topic}")
                        logging.info(f"Downloaded images successfully")
                        logging.info(f"Added images to video successfully")
                        # Add audio and subtitles to the cut video
                        clip = ai_short_gen.add_audio_and_captions_to_video(cut_video_path, audio_path, 'assets/subtitles.srt')  # Add audio and subtitles to the cut video
                        ai_short_gen.add_images_to_video(clip, image_paths) 
                    else:
                        logging.error("Failed to cut video.")  # Log if cutting the video fails
                else:
                    logging.error("Calculated start time is invalid.")  # Log if start time calculation fails
        else:
            logging.error("Failed to generate script.")  # Log if script generation fails
    else:
        logging.error("Failed to download video.")  # Log if video download fails

# Run the main function in an asyncio event loop
import asyncio
asyncio.run(main())
