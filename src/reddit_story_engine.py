import yaml
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, CompositeAudioClip, ColorClip
import random
from openai import OpenAI
import os
import re

# Set up logging
logging.basicConfig(level=logging.INFO)

from .image_handler import ImageHandler
from .video_editor import VideoEditor
from .captions.caption_handler import CaptionHandler

def load_prompt(file_path):
    """Load the YAML prompt template file."""
    try:
        with open(file_path, 'r') as file:
            prompt_template_file = yaml.safe_load(file)
        return prompt_template_file
    except FileNotFoundError:
        logging.error(f"Prompt file {file_path} not found.")
        raise
    except Exception as e:
        logging.error(f"Error loading prompt file: {e}")
        raise

# Update the config loading to use the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))

# Accessing configuration values
openai_api_key = os.getenv('OPENAI_API_KEY')
pexels_api_key = os.getenv('PEXELS_API_KEY')

openai = OpenAI(api_key=openai_api_key)

class RedditStoryGenerator:
    def __init__(self):
        self.video_editor: VideoEditor = VideoEditor()
        self.image_handler: ImageHandler = ImageHandler(pexels_api_key, openai_api_key)
        self.caption_handler: CaptionHandler = CaptionHandler()

    def gpt_summary_of_script(self, video_script: str) -> str:
        try:
            completion = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                temperature=0.25,
                max_tokens=250,
                messages=[
                    {"role": "user", "content": f"Summarize the following video script; it is very important that you keep it to one line. \n Script: {video_script}"}
                ]
            )
            logging.info("Script generated successfully.")
            return completion.choices[0].message.content
        except Exception as e:
            logging.error(f"Error generating script summary: {e}")
            return ""  # Return an empty string on error

    async def create_reddit_question_clip(self, reddit_question: str, video_height: int = 720) -> tuple[TextClip, str]:
        """Create a text clip for the Reddit question and generate its audio."""
        try:
            # Generate audio for the Reddit question
            reddit_question_audio_path: str = await self.video_editor.generate_voice(reddit_question)

            reddit_question_audio_clip: AudioFileClip = AudioFileClip(reddit_question_audio_path)
            reddit_question_audio_duration: float = reddit_question_audio_clip.duration
            reddit_question_audio_clip.close()

            # Calculate text clip size based on video width
            text_width = int((video_height * 9 / 16) * 0.7)  # 90% of video width after cropped to 9/16
            text_height = int(text_width * 0.35)  # 30% of cropped video width

            # Create a text clip for the Reddit question
            reddit_question_text_clip = TextClip(
                reddit_question,
                fontsize=int(video_height * 0.03),  # 2.5% of video height for font size
                color='black',
                bg_color='white',
                size=(text_width, text_height),  # Allow height to adjust automatically
                method='caption',
                align='center'
            ).set_duration(reddit_question_audio_duration)

            return reddit_question_text_clip, reddit_question_audio_path
        except Exception as e:
            logging.error(f"Error creating Reddit question clip: {e}")
            return None, None

    async def generate_video(self, video_path_or_url: str = '', 
                            video_path: str = '', 
                            video_url: str = '', 
                            video_topic: str = '',
                            captions_settings: dict = {},
                            add_images: bool = True
                            ) -> dict:
        """Generate a video based on the provided topic or ready-made script.

        Args:
            video_path_or_url (str): 'video_path' or 'video_url', depending on which one is provided.
            video_path (str): The path of the video if provided.
            video_url (str): The URL of the video to download.
            video_topic (str): The topic of the video if script type is 'based_on_topic'.        
            captions_settings (dict): The settings for the captions. (font, color, etc)

        Returns:
            dict: A dictionary with the status of the video generation and a message.
        """
        clips_to_close = []
        try:
            if not video_path_or_url:
                raise ValueError("video_path_or_url cannot be empty.")

            if not video_path and not video_url:
                raise ValueError("Either video_path or video_url must be provided.")

            if not video_topic:
                raise ValueError("For 'based_on_topic', the video topic should not be null.")
            
            """ Download or getting video """
            video_path: str = video_path if video_path_or_url == 'video_path' else self.video_editor.download_video(video_url)
            if not video_path:
                logging.error("Failed to download video.")
                return {"status": "error", "message": "No video path provided."}
            # Get video dimensions
            with VideoFileClip(video_path) as video:
                video_width, video_height = video.w, video.h

            """ Handle Script Generation and Process """
            # Load prompt template
            current_dir:str = os.path.dirname(os.path.abspath(__file__))   
            prompt_template_path:str = os.path.join(current_dir, '..', 'prompt_templates', 'reddit_thread.yaml')
            if not os.path.exists(prompt_template_path):
                logging.error(f"Prompt template file {prompt_template_path} not found.")
                raise FileNotFoundError(f"Prompt template file {prompt_template_path} not found.")
            prompt_template: str = load_prompt(prompt_template_path)
            # Generate the script or use the provided script
            script: dict =  await self.video_editor.generate_script(video_topic, prompt_template)
            reddit_question: str = script['reddit_question']
            youtube_short_story: str = script['youtube_short_story']
            if not script:
                logging.error("Failed to generate script.")
                return {"status": "error", "message": "Failed to generate script."}

            """ Define video length for each clip (question and story) """
            # Initialize Reddit clips
                        # Create the Reddit question clip with the actual video width
            reddit_question_text_clip, reddit_question_audio_path = await self.create_reddit_question_clip(reddit_question, video_height)
            reddit_question_audio_clip: AudioFileClip = AudioFileClip(reddit_question_audio_path)
            reddit_question_audio_duration: float = reddit_question_audio_clip.duration
            clips_to_close.append(reddit_question_audio_clip)
            # Initialize Background video
            background_video_clip: VideoFileClip = VideoFileClip(video_path)
            clips_to_close.append(background_video_clip)
            background_video_length: float = background_video_clip.duration
            ## Initialize Story Audio
            story_audio_path: str = await self.video_editor.generate_voice(youtube_short_story)
            if not story_audio_path:
                logging.error("Failed to generate audio.")
                return {"status": "error", "message": "Failed to generate audio."}

            story_audio_clip: AudioFileClip = AudioFileClip(story_audio_path)
            clips_to_close.append(story_audio_clip)
            story_audio_length: float = story_audio_clip.duration
        
            # Calculate video times to cut clips
            max_start_time: float = background_video_length - story_audio_length - reddit_question_audio_duration
            start_time: float = random.uniform(0, max_start_time)
            end_time: float = start_time + reddit_question_audio_duration + story_audio_length
            
            """ Cut video once """
            cut_video_path: str = self.video_editor.cut_video(video_path, start_time, end_time)
            cut_video_clip = VideoFileClip(cut_video_path)
            clips_to_close.append(cut_video_clip)

            """ Handle reddit question video """
            reddit_question_video = cut_video_clip.subclip(0, reddit_question_audio_duration)
            reddit_question_video = reddit_question_video.set_audio(reddit_question_audio_clip)
            reddit_question_video = self.video_editor.crop_video_9_16(reddit_question_video)

            # Add the text clip to the video
            reddit_question_video = CompositeVideoClip([
                reddit_question_video,
                reddit_question_text_clip.set_position(('center', 'center'))
            ])

            """ Handle story video """
            story_video = cut_video_clip.subclip(reddit_question_audio_duration)
            story_video = story_video.set_audio(story_audio_clip)
            story_video = self.video_editor.crop_video_9_16(story_video)

            font_size = video_width * 0.025

            # Generate subtitles
            story_subtitles_path, story_subtitles_clips = await self.caption_handler.process(
                story_audio_path,
                captions_settings.get('color', 'white'),
                captions_settings.get('shadow_color', 'black'),
                captions_settings.get('font_size', font_size),
                captions_settings.get('font', 'LEMONMILK-Bold.otf')
            )

            video_context: str = video_topic
            story_image_paths = self.image_handler.get_images_from_subtitles(story_subtitles_path, video_context, story_audio_length) if add_images else []
            story_video = self.video_editor.add_images_to_video(story_video, story_image_paths)
            
            story_video = self.video_editor.add_captions_to_video(story_video, story_subtitles_clips)
            # Combine clips
            combined_clips = CompositeVideoClip([
                reddit_question_video,
                story_video.set_start(reddit_question_audio_duration)
            ])

            final_video_output_path = self.video_editor.render_final_video(combined_clips)
            
            # Cleanup: Ensure temporary files are removed
            self.video_editor.cleanup_files([story_audio_path, cut_video_path, story_subtitles_path, reddit_question_audio_path], story_image_paths)
            
            logging.info(f"FINAL OUTPUT PATH: {final_video_output_path}")
            return {"status": "success", "message": "Video generated successfully.", "output_path": final_video_output_path}
        
        except Exception as e:
            logging.error(f"Error in video generation: {e}")
            return {"status": "error", "message": f"Error in video generation: {str(e)}"}
        finally:
            # Close all clips
            for clip in clips_to_close:
                clip.close()
