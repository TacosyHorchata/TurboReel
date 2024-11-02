import json
import os
import logging
import uuid
import math

from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip, ColorClip, concatenate_audioclips

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .utils.llm_calls import generate_voice
from .utils.images_generation import search_pexels_images, search_pixabay_images, download_image, generate_image_pollinations

from ..captions.caption_handler import CaptionHandler

class PyJson2Video:

    def __init__(self, json_input, output_video_path: str):
        self.json_input = json_input
        self.output_video_path = output_video_path
        self.data = None
        self.video_clips = []
        self.audio_clips = []
        self.caption_handler = CaptionHandler()
        self.temp_files = []  # Add this to track all temporary files

    async def convert(self):
        try:
            self._load_json()
            await self.parse_script()
            self.parse_videos()
            await self.parse_images()
            self.parse_audio()
            self.parse_text()
            
            extra_args = self.parse_extra_args()
            
            return await self._create_final_clip(extra_args)
        except Exception as e:
            logger.error(f"An error occurred during conversion: {str(e)}")
            raise
        finally:
            # Clean up all temporary files
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.debug(f"Removed temporary file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {e}")

    def _load_json(self):
        try:
            if isinstance(self.json_input, dict):
                self.data = self.json_input
            elif isinstance(self.json_input, str):
                with open(self.json_input, 'r') as f:
                    self.data = json.load(f)
            else:
                raise ValueError("Invalid JSON input. Expected dict or file path string.")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON input: {self.json_input}")
            raise
        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.json_input}")
            raise

    def parse_videos(self):
        resolution = self.data.get('extra_args', {}).get('resolution', {'width': 1920, 'height': 1080})
        max_width, max_height = resolution['width'], resolution['height']

        for video in self.data.get('videos', []):
            try:
                # Check if the video file is an MP4
                if not video['video_path'].lower().endswith('.mp4'):
                    raise ValueError(f"Invalid video format. Only MP4 files are supported: {video['video_path']}")
                
                clip = VideoFileClip(video['video_path'])
                clip = clip.subclip(float(video['start_time']), float(video['end_time']))
                clip = clip.resize(height=int(resolution['height']))
                
                # Handle position
                position = video.get('position', [50, 50])  # Default to center if not specified
                if isinstance(position, list) and len(position) == 2:
                    # Convert position to relative coordinates
                    rel_x = position[0] / 100 * max_width
                    rel_y = position[1] / 100 * max_height
                    
                    # Adjust position to center the video
                    center_x = rel_x - clip.w / 2
                    center_y = rel_y - clip.h / 2
                    
                    clip = clip.set_position((center_x, center_y))
                else:
                    logger.warning(f"Invalid position for video {video.get('video_path')}: {position}")
                    clip = clip.set_position('center')
                
                clip = clip.set_opacity(float(video['opacity']))
                clip = clip.volumex(float(video['volume']))


                start_time = self._get_time(video, 'start_time')
                end_time = self._get_time(video, 'end_time')

                clip = clip.set_start(start_time).set_duration(end_time - start_time)

                self.video_clips.append(clip)
                logger.info(f"Video {video.get('video_path')} added to video clips, start time: {start_time}, end time: {end_time}")
            except Exception as e:
                logger.error(f"Error processing video {video.get('video_path')}: {str(e)}")
                raise

    async def parse_images(self):
        resolution = self.data.get('extra_args', {}).get('resolution', {'width': 1920, 'height': 1080})
        max_width, max_height = resolution['width'], resolution['height']

        for image in self.data.get('images', []):
            source_type = image.get('source_type', 'prompt')
            
            try:
                # Get image source
                image_source = None
                image_urls = []
                
                if source_type == 'path':
                    image_source = image['source_content']
                elif source_type == 'prompt':
                    query = image['source_content']
                    # Try different image sources in sequence
                    image_urls = generate_image_pollinations(query)
                    if not image_urls:
                        logger.info("Trying Pexels as fallback...")
                        image_urls = search_pexels_images(query)
                    if not image_urls:
                        logger.info("Trying Pixabay as final fallback...")
                        image_urls = search_pixabay_images(query)
                    
                    if image_urls:
                        image_source = download_image(image_urls[0])
                        if image_source:
                            self.temp_files.append(image_source)  # Track downloaded image
                    else:
                        logger.error(f"No images found for prompt: {query}")
                        continue
                elif source_type == 'url':
                    image_source = download_image(image['source_content'])
                    if image_source:
                        self.temp_files.append(image_source)  # Track downloaded image

                # Create and process the image clip
                clip = ImageClip(image_source)
                
                # Handle 'full' argument and determine target dimensions
                if image.get('max_width') == 'full':
                    target_width = max_width
                else:
                    target_width = min(int(image.get('max_width', max_width)), max_width)

                if image.get('max_height') == 'full':
                    target_height = max_height
                else:
                    target_height = min(int(image.get('max_height', max_height)), max_height)

                # Calculate the scaling factor to maintain aspect ratio with 10% zoom
                width_ratio = (target_width / clip.w) * 1.1  # 10% zoom
                height_ratio = (target_height / clip.h) * 1.1  # 10% zoom
                scale_factor = min(width_ratio, height_ratio)

                # Resize the clip with zoom
                new_width = math.ceil(clip.w * scale_factor)
                new_height = math.ceil(clip.h * scale_factor)
                clip = clip.resize(width=new_width, height=new_height)
                
                # Handle position
                position = image.get('position', [50, 50]) # Default to center if not specified
                if isinstance(position, list) and len(position) == 2:
                    # Convert position to relative coordinates
                    rel_x = position[0] / 100 * max_width
                    rel_y = position[1] / 100 * max_height
                    
                    # Adjust position to center the image
                    center_x = rel_x - new_width / 2
                    center_y = rel_y - new_height / 2
                    
                    clip = clip.set_position((center_x, center_y))
                else:
                    logger.warning(f"Invalid position for image {image.get('image_path')}: {position}")
                    clip = clip.set_position('center')

                clip = clip.set_opacity(float(image.get('opacity', 1.0)))
                if 'rotation' in image:
                    clip = clip.rotate(float(image.get('rotation', 0)))
                
                start_time = self._get_time(image, 'start_time')
                end_time = self._get_time(image, 'end_time')
                
                clip = clip.set_start(start_time).set_duration(end_time - start_time)

                self.video_clips.append(clip)
                logger.info(f"Image {image.get('source_content')} added to video clips, start time: {start_time}, end time: {end_time}")
            except Exception as e:
                logger.error(f"Error processing image {image.get('image_id', 'unknown')}: {str(e)}")
                continue

    def parse_audio(self):
        for audio in self.data.get('audio', []):
            try:
                # If the audio is a temporary file (e.g., downloaded or generated)
                if audio.get('is_temp', False):
                    self.temp_files.append(audio['audio_path'])
                
                clip = AudioFileClip(audio['audio_path'])
                #clip = clip.subclip(float(audio['start_time']), float(audio['end_time']))
                clip = clip.volumex(float(audio['volume']))

                start_time = self._get_time(audio, 'start_time')
                end_time = self._get_time(audio, 'end_time')
                
                clip = clip.set_start(start_time).set_duration(end_time - start_time)
                
                self.audio_clips.append(clip)
                logger.info(f"Audio {audio.get('audio_path')} added to audio clips, start time: {start_time}, end time: {end_time}")
            except Exception as e:
                logger.error(f"Error processing audio {audio.get('audio_path')}: {str(e)}")
                raise

    async def parse_script(self):
        resolution = self.data.get('extra_args', {}).get('resolution', {'width': 1920, 'height': 1080})
        max_width, max_height = resolution['width'], resolution['height']

        last_end_time = 0  # Keep track of the last end time

        for index, script in enumerate(self.data.get('script', [])):
            try:
                audio_path = await generate_voice(script['text'])
                self.temp_files.append(audio_path)  # Track generated voice audio
                script_clip = AudioFileClip(audio_path)
                
                # Determine start time based on the previous end_time script item
                if index > 0:
                    start_time = self._get_time(self.data['script'][index-1], 'end_time')
                else:
                    start_time = 0

                # Calculate timings
                voice_start_time = start_time + script.get('voice_start_time', 0)
                post_pause_duration = script.get('post_pause_duration', 0)

                clip_duration = script_clip.duration
                end_time = voice_start_time + clip_duration + post_pause_duration
                voice_end_time = voice_start_time + clip_duration
                
                # Update the script item with calculated start and end times
                self.data['script'][index]['start_time'] = start_time
                self.data['script'][index]['voice_start_time'] = voice_start_time
                self.data['script'][index]['voice_end_time'] = voice_end_time
                self.data['script'][index]['end_time'] = end_time

                # Set the clip's start time and duration
                script_clip = script_clip.set_start(voice_start_time).set_duration(clip_duration)

                self.audio_clips.append(script_clip)
                logger.info(f"Audio {audio_path} added to audio clips, start time: {start_time}, end time: {end_time}")
                # Update the last end time
                last_end_time = end_time

            except Exception as e:
                logger.error(f"Error processing script: {script.get('text')}: {str(e)}")
                raise

        # After processing all scripts, update the total duration of the video
        self.total_duration = max(clip.end for clip in self.audio_clips + self.video_clips)

    def parse_text(self):
        resolution = self.data.get('extra_args', {}).get('resolution', {'width': 1920, 'height': 1080})
        max_width, max_height = resolution['width'], resolution['height']

        for text in self.data.get('text', []):
            try:
                
                content = text.get('content')
                font = text.get('font', 'Arial')
                size = (int(max_width * 0.8), None)
                color = text.get('color', 'white')
                fontsize = min(int(text.get('font_size', int(max_height * 0.06))), int(max_height * 0.06))
                shadow_color = text.get('shadow_color', 'black')
                shadow_offset = fontsize / 15

                clip = TextClip(
                    content,
                    size=size,
                    fontsize=fontsize,
                    font=font,
                    color=color,
                    method='caption',
                    align='center'
                )
                shadow_clip = TextClip(content, fontsize=fontsize, font=font, color=shadow_color, size=size, method='caption')
                shadow_clip = shadow_clip.set_position((shadow_offset, shadow_offset))
                
                # Composite all layers
                composite_clip = CompositeVideoClip([shadow_clip, clip])
                
                # Handle position
                position = text.get('position', [50, 50])  # Default to center if not specified
                if isinstance(position, list) and len(position) == 2:
                    # Convert position to relative coordinates
                    rel_x = position[0] / 100 * max_width
                    rel_y = position[1] / 100 * max_height
                        
                    # Adjust position to center the text
                    center_x = rel_x - clip.w / 2
                    center_y = rel_y - composite_clip.h / 2
                        
                    composite_clip = composite_clip.set_position((center_x, center_y))
                else:
                    logger.warning(f"Invalid position for script text: {text.get('text')}: {position}")
                    composite_clip = composite_clip.set_position('center')
  
                start_time = self._get_time(text, 'start_time')
                end_time = self._get_time(text, 'end_time')
                
                composite_clip = composite_clip.set_start(start_time).set_duration(end_time - start_time)
                
                self.video_clips.append(composite_clip)
                logger.info(f"Text {text.get('content')} added to video clips, start time: {start_time}, end time: {end_time}")
            except Exception as e:
                logger.error(f"Error processing script text: {text.get('text')}: {str(e)}")
                raise

    def parse_extra_args(self):
        try:
            extra_args = self.data.get('extra_args', {})
            return extra_args
        except Exception as e:
            logger.error(f"Error parsing extra arguments: {str(e)}")
            raise

    async def _create_final_clip(self, extra_args:dict) -> str:
        temp_files = []  # Track temporary files for cleanup
        try:
            resolution = extra_args.get('resolution', {'width': 1920, 'height': 1080})
            background_color = extra_args.get('background_color', [249, 249, 249])
            captions_settings = extra_args.get('captions', {})
            
            # If background_color is a string, convert it to RGB
            if isinstance(background_color, str):
                if background_color.lower() == 'white':
                    background_color = [255, 255, 255]
                elif background_color.lower() == 'black':
                    background_color = [0, 0, 0]
            
            # Create a blank background clip if no video clips exist
            if not self.video_clips:
                logger.warning("No video clips found, creating blank background clip")
                # Calculate duration from audio clips or use default
                duration = max([clip.end for clip in self.audio_clips]) if self.audio_clips else 10
                blank_clip = ColorClip(
                    size=(resolution['width'], resolution['height']),
                    color=background_color,
                    duration=duration
                )
                self.video_clips.append(blank_clip)
            
            # Process captions for all script audio clips
            if captions_settings.get('enabled', False):
                script_audio_clips = [clip for clip in self.audio_clips if hasattr(clip, 'filename')]
                if script_audio_clips:
                    # Concatenate all audio clips
                    final_audio = concatenate_audioclips(script_audio_clips)
                    
                    # Save the concatenated audio temporarily
                    temp_audio_path = os.path.join(os.path.dirname(__file__), 'assets', f"temp_combined_audio_{uuid.uuid4()}.wav")
                    temp_files.append(temp_audio_path)  # Track for cleanup
                    final_audio.write_audiofile(temp_audio_path)
                    
                    # Generate captions
                    subtitles_path, subtitle_clips = await self.caption_handler.process(
                        temp_audio_path,
                        captions_settings.get('color', 'white'),
                        captions_settings.get('background_color', 'black'),
                        captions_settings.get('font_size', resolution['height'] * 0.05),
                        captions_settings.get('font', 'LEMONMILK-Bold.otf'),
                        resolution['width']
                    )
                    if subtitles_path:
                        temp_files.append(subtitles_path)  # Track for cleanup
                    
                    self.video_clips.extend(subtitle_clips)
            
            final_clip = CompositeVideoClip(
                self.video_clips,
                size=(resolution['width'], resolution['height']),
                bg_color=background_color
            )
            
            # Add audio to the final clip
            if self.audio_clips:
                final_audio = CompositeAudioClip(self.audio_clips)
                final_clip = final_clip.set_audio(final_audio)
            
            # Write the final video file
            final_clip.write_videofile(
                self.output_video_path,
                fps=30,
                codec='libx264',
                preset='veryfast',
                audio_codec='aac'
            )

            # Close all clips to free up resources
            final_clip.close()
            if hasattr(final_clip, 'audio') and final_clip.audio is not None:
                final_clip.audio.close()
            
            # Close all source clips
            for clip in self.video_clips:
                clip.close()
            for clip in self.audio_clips:
                clip.close()

            return self.output_video_path
        except Exception as e:
            logger.error(f"Error creating final clip: {str(e)}")
            raise
        finally:
            # Clean up all temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.debug(f"Removed temporary file: {temp_file}")
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {e}")
    
    def _get_time(self, asset, time_key: str) -> float:
        time_value = asset.get(time_key)

        if isinstance(time_value, (int, float)):
            return float(time_value)

        if isinstance(time_value, str):
            time_parts = time_value.split('.')
            if len(time_parts) != 2:
                raise ValueError(f"Invalid {time_key}: {time_value}")

            time_id, time_type = time_parts
            item = next((item for item in self.data.get('script', []) if item['_id'] == time_id), None)
            if item:
                if time_type == 'voice_start_time':
                    return item.get('voice_start_time')
                elif time_type == 'voice_end_time':
                    return item.get('voice_end_time')
                elif time_type == 'end_time':
                    return item.get('end_time', 'voice_end_time')
                elif time_type == 'start_time':
                    return item.get('start_time', 'voice_start_time')

        raise ValueError(f"Unable to determine {time_key} for: {time_value}")




