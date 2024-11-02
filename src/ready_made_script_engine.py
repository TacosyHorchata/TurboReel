import yaml
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, CompositeAudioClip, ColorClip
import random
from openai import OpenAI
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

from .image_handler import ImageHandler
from .video_editor import VideoEditor
from .captions.caption_handler import CaptionHandler

# Update the config loading to use the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))

# Accessing configuration values
openai_api_key = os.getenv('OPENAI_API_KEY')
pexels_api_key = os.getenv('PEXELS_API_KEY')

openai = OpenAI(api_key=openai_api_key)

class ReadyMadeScriptGenerator:
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

    async def create_hook_text_clip(self, hook: str, video_height: int = 720) -> tuple[TextClip, str]:
        """Create a text clip for the hook and generate its audio."""
        try:
            # Generate audio for the hook
            hook_audio_path: str = await self.video_editor.generate_voice(hook)

            hook_audio_clip: AudioFileClip = AudioFileClip(hook_audio_path)
            hook_audio_duration: float = hook_audio_clip.duration
            hook_audio_clip.close()

            # Calculate text clip size based on video width
            text_width = int((video_height * 9 / 16) * 0.7)  # 90% of video width after cropped to 9/16
            text_height = int(text_width * 0.35)  # 30% of cropped video width

            # Create a text clip for the Reddit question
            hook_text_clip = TextClip(
                hook,
                fontsize=int(video_height * 0.03),  # 2.5% of video height for font size
                color='black',
                bg_color='white',
                size=(text_width, text_height),  # Allow height to adjust automatically
                method='caption',
                align='center'
            ).set_duration(hook_audio_duration)

            return hook_text_clip, hook_audio_path
        except Exception as e:
            logging.error(f"Error creating hook clip: {e}")
            return None, None
        
    async def generate_hook(self, video_script: str) -> str:
        """Generate a hook for the video script."""
        try:

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                temperature=0.25,
                max_tokens=250,
                messages=[
                    {"role": "user", "content": f"Generate a hook for the following video script; it is very important that you keep it to one line. \n Script: {video_script}"}
                ]
            )
            hook = response.choices[0].message.content

            return hook
        except Exception as e:
            logging.error(f"Error generating hook: {e}")
            return ""

    async def generate_video(self, video_path_or_url: str = '', 
                            video_path: str = '', 
                            video_url: str = '', 
                            video_script: str = '',
                            video_hook: str = '',
                            captions_settings: dict = {}, # font, color, font_size, shadow_color
                            add_images: bool = True
                            ) -> dict:
        """Generate a video based on the provided topic or ready-made script.

        Args:
            video_path_or_url (str): 'video_path' or 'video_url', depending on which one is provided.
            video_path (str): The path of the video if provided.
            video_url (str): The URL of the video to download.
            video_script (str): The script of the video.        
            captions_settings (dict): The settings for the captions. (font, color, etc)

        Returns:
            dict: A dictionary with the status of the video generation and a message.
        """
        clips_to_close = []
        try:
            if not video_path_or_url:
                logging.error("video_path_or_url cannot be empty.")
                return {"status": "error", "message": "video_path_or_url cannot be empty."}
                

            if not video_path and not video_url:
                logging.error("Either video_path or video_url must be provided.")
                return {"status": "error", "message": "Either video_path or video_url must be provided."}

            if not video_script:
                logging.error("The video script should not be null.")
                return {"status": "error", "message": "The video script should not be null."}
            
            if len(video_script) > 1300:
                logging.error("The video script should not be longer than 1300 characters.")
                return {"status": "error", "message": "The video script should not be longer than 1300 characters."}
            
            if len(video_hook) > 80:
                logging.error("The video hook should not be longer than 80 characters.")
                return {"status": "error", "message": "The video hook should not be longer than 80 characters."}

            """ Download or getting video """
            video_path: str = video_path if video_path_or_url == 'video_path' else self.video_editor.download_video(video_url)
            if not video_path:
                logging.error("No video path provided.")
                return {"status": "error", "message": "No video path provided."}
            # Get video dimensions
            with VideoFileClip(video_path) as video:
                video_width, video_height = video.w, video.h

            """ Handle Script Generation and Process """
            # Load prompt template
            current_dir = os.path.dirname(os.path.abspath(__file__))   
            prompt_template_path = os.path.join(current_dir, '..', 'prompt_templates', 'reddit_thread.yaml')
            if not os.path.exists(prompt_template_path):
                logging.error(f"Prompt template file {prompt_template_path} not found.")
                raise FileNotFoundError(f"Prompt template file {prompt_template_path} not found.")
            # Generate the script or use the provided script
            hook = video_hook if video_hook else await self.generate_hook(video_script)
            youtube_short_story = video_script
            if not youtube_short_story:
                logging.error("Failed to generate script.")
                return {"status": "error", "message": "Failed to generate script."}

            """ Define video length for each clip (question and story) """
            # Initialize Reddit clips
            # Create the Reddit question clip with the actual video width
            hook_text_clip, hook_audio_path = await self.create_hook_text_clip(hook, video_height)
            hook_audio_clip = AudioFileClip(hook_audio_path)
            hook_audio_duration = hook_audio_clip.duration
            clips_to_close.append(hook_audio_clip)
            # Initialize Background video
            background_video_clip = VideoFileClip(video_path)
            clips_to_close.append(background_video_clip)
            background_video_length = background_video_clip.duration
            ## Initialize Story Audio
            story_audio_path = await self.video_editor.generate_voice(youtube_short_story)
            if not story_audio_path:
                logging.error("Failed to generate audio.")
                return {"status": "error", "message": "Failed to generate audio."}

            story_audio_clip = AudioFileClip(story_audio_path)
            clips_to_close.append(story_audio_clip)
            story_audio_length = story_audio_clip.duration
        
            # Calculate video times to cut clips
            max_start_time: float = background_video_length - story_audio_length - hook_audio_duration
            start_time: float = random.uniform(0, max_start_time)
            end_time: float = start_time + hook_audio_duration + story_audio_length
            
            """ Cut video once """
            cut_video_path: str = self.video_editor.cut_video(video_path, start_time, end_time)
            cut_video_clip = VideoFileClip(cut_video_path)
            clips_to_close.append(cut_video_clip)

            """ Handle hook video """
            hook_video = cut_video_clip.subclip(0, hook_audio_duration)
            hook_video = hook_video.set_audio(hook_audio_clip)
            hook_video = self.video_editor.crop_video_9_16(hook_video)

            # Add the text clip to the video
            hook_video = CompositeVideoClip([
                hook_video,
                hook_text_clip.set_position(('center', 'center'))
            ])

            """ Handle story video """
            story_video = cut_video_clip.subclip(hook_audio_duration)
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

            video_context = self.gpt_summary_of_script(youtube_short_story)
            story_image_paths = self.image_handler.get_images_from_subtitles(story_subtitles_path, video_context, story_audio_length) if add_images else []
            story_video = self.video_editor.add_images_to_video(story_video, story_image_paths)
            
            story_video = self.video_editor.add_captions_to_video(story_video, story_subtitles_clips)
            # Combine clips
            combined_clips = CompositeVideoClip([
                hook_video,
                story_video.set_start(hook_audio_duration)
            ])

            final_video_output_path = self.video_editor.render_final_video(combined_clips)
            
            # Cleanup: Ensure temporary files are removed
            self.video_editor.cleanup_files([story_audio_path, cut_video_path, story_subtitles_path, hook_audio_path], story_image_paths)
            
            logging.info(f"FINAL OUTPUT PATH: {final_video_output_path}")
            return {"status": "success", "message": "Video generated successfully.", "output_path": final_video_output_path}
        
        except Exception as e:
            logging.error(f"Error in video generation: {e}")
            return {"status": "error", "message": f"Error in video generation: {str(e)}"}
        finally:
            # Close all clips
            for clip in clips_to_close:
                clip.close()
