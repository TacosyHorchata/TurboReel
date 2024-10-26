import json
import os
import logging
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .utils.llm_calls import generate_voice
from .utils.images_generation import search_pexels_images, search_pixabay_images, download_image

"""
Example of the json file:


{
    "videos": [
        {
            "video_path": "path/to/video.mp4",
            "start_time": 0,
            "end_time": 10,
            "max_width": 1920,
            "max_height": 1080,
            "z_index": 1,
            "position": [0, 0],
            "opacity": 1.0,
            "volume": 1.0,
            "order": 1
        },
        {
            "video_path": "path/to/video2.mp4",
            "start_time": 10,
            "end_time": 20,
            "max_width": 960,
            "max_height": 540,
            "z_index": 1,
            "position": [100, 100],
            "opacity": 0.8,
            "volume": 0.5,
            "order": 2
        }
    ],
    "images": [
        {
            "image_id": "img_1234567890",
            "source_type": "path", # "path", "url", "prompt"
            "source_content": "path/to/image.png", # path to the image file or url to the image or prompt to generate the image
            "start_time": 0, 
            "end_time": 10, 
            "max_width": 500,
            "max_height": 300,
            "z_index": 3,
            "position": [50, 50],
            "opacity": 1.0,
            "rotation": 0
        }
    ],
    "audio": [
        {
            "_id": "aud_1234567890",
            "audio_path": "path/to/audio.mp3",
            "start_time": 0,
            "end_time": 10,
            "volume": 0.2,
        }
    ],
    "script": [
        {
            "_id": "scr_1234567890",
            "text": "Hello, world!",
            "voice_start_time": 0,
            "post_pause_duration": 0
        },
        {
            "_id": "scr_1234567891",
            "text": "This is an AI video editor!",
            "start_time": "scr_1234567890.end_time"
        },
        {
            "_id": "scr_1234567892",
            "text": "Also this is a test!",
            "start_time": "scr_1234567891.end_time"
        }
    ],
    "text": [
        {
            "_id": "txt_1234567890",
            "text": "Hello, world!",
            "start_time": 0,
            "end_time": "scr_1234567890.end_time",
            "font": "Arial",
            "font_size": 48,
            "color": "white",
            "position": [50, 50],
            "z_index": 4
        }
    ],
    "extra_args": {
        "resolution": {
            "width": 1920,
            "height": 1080
        },
        "captions": {
            "enabled": false,
            "language": "en",
            "font": "Arial",
            "font_size": 24,
            "color": "white",
            "background_color": "black",
            "background_opacity": 0.7,
            "position": [50, 50],
            "align": "center",
            "max_lines": 1,
            "words_per_line": 2
        },
        "audio_language": "en",
        "voice_id": "alloy",
        "background_color": "black",
        "output_format": "mp4"
    }
}

"""


class PyJson2Video:
    def __init__(self, json_input, output_video_path: str):
        self.json_input = json_input
        self.output_video_path = output_video_path
        self.data = None
        self.video_clips = []
        self.audio_clips = []

    async def convert(self):
        try:
            self._load_json()
            await self.parse_script()
            self.parse_videos()
            await self.parse_images()
            self.parse_audio()
            self.parse_text()
            
            extra_args = self.parse_extra_args()
            
            return self._create_final_clip(extra_args)
        except Exception as e:
            logger.error(f"An error occurred during conversion: {str(e)}")
            raise

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
            source_type = image.get('source_type')
            # check that the source_type is valid
            if source_type not in ['path', 'url', 'prompt']:
                source_type = 'prompt'
            
            try:
                if source_type == 'path':
                    image_source = image['source_content']
                elif source_type == 'prompt':
                    # Generate the image
                    try:
                        image_url = search_pexels_images(image['source_content'])
                        if not image_url:
                            image_url = search_pixabay_images(image['source_content'])
                        logger.info(f"Image URL: {image_url}")
                        if not image_url:
                            raise ValueError("No image URL returned from search_pexels_images")
                        image_source = download_image(image_url)
                    except Exception as e:
                        logger.error(f"Error searching or downloading image: {str(e)}")
                        continue  # Skip this image and move to the next one
                elif source_type == 'url':
                    # Download the image
                    image_source = download_image(image['source_content'])

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

                # Calculate the scaling factor to maintain aspect ratio
                width_ratio = target_width / clip.w
                height_ratio = target_height / clip.h
                scale_factor = min(width_ratio, height_ratio)

                # Resize the clip maintaining aspect ratio
                new_width = int(clip.w * scale_factor)
                new_height = int(clip.h * scale_factor)
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

                clip = clip.set_opacity(float(image['opacity']))
                if 'rotation' in image:
                    clip = clip.rotate(float(image['rotation']))
                
                start_time = self._get_time(image, 'start_time')
                end_time = self._get_time(image, 'end_time')
                
                clip = clip.set_start(start_time).set_duration(end_time - start_time)

                self.video_clips.append(clip)
                logger.info(f"Image {image.get('source_content')} added to video clips, start time: {start_time}, end time: {end_time}")
            except Exception as e:
                logger.error(f"Error processing image {image.get('source_content')}: {str(e)}")
                continue  # Skip this image and move to the next one

    def parse_audio(self):
        for audio in self.data.get('audio', []):
            try:
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
                clip = TextClip(
                    text['content'],
                    fontsize=int(text['font_size']),
                    font=text['font'],
                    color=text['color']
                )
                
                # Handle position
                position = text.get('position', [50, 50])  # Default to center if not specified
                if isinstance(position, list) and len(position) == 2:
                    # Convert position to relative coordinates
                    rel_x = position[0] / 100 * max_width
                    rel_y = position[1] / 100 * max_height
                        
                    # Adjust position to center the text
                    center_x = rel_x - clip.w / 2
                    center_y = rel_y - clip.h / 2
                        
                    clip = clip.set_position((center_x, center_y))
                else:
                    logger.warning(f"Invalid position for script text: {text.get('text')}: {position}")
                    clip = clip.set_position('center')
  
                start_time = self._get_time(text, 'start_time')
                end_time = self._get_time(text, 'end_time')
                
                clip = clip.set_start(start_time).set_duration(end_time - start_time)
                
                self.video_clips.append(clip)
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

    def _create_final_clip(self, extra_args:dict) -> str:
        try:
            # Create the final composite video
            resolution = extra_args.get('resolution', {'width': 1920, 'height': 1080})
            final_clip = CompositeVideoClip(self.video_clips, size=(resolution['width'], resolution['height']))
            
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
            return self.output_video_path
        except Exception as e:
            logger.error(f"Error creating final clip: {str(e)}")
            raise
    
    
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




