import asyncio
from src.generateVideo import generate_video
import yaml

with open('./config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Example usage
video_path_or_url = config['assets']['VIDEO_PATH_OR_URL']
video_url = config['assets']['VIDEO_YOUTUBE_URL']
video_path = config['assets']['VIDEO_PATH']
video_topic = config['video_parameters']['VIDEO_TOPIC']
video_script = config['video_parameters']['VIDEO_SCRIPT']
video_script_type = config['video_parameters']['VIDEO_SCRIPT_TYPE']

asyncio.run(generate_video(
    video_path_or_url=video_path_or_url, 
    video_path=video_path,
    video_url=video_url, 
    video_topic=video_topic, 
    video_script=video_script, 
    video_script_type=video_script_type))
