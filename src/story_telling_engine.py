import json
import yaml
import os
import uuid
import logging

from .json_2_video_engine.json_2_video import PyJson2Video
from .video_editor import VideoEditor

logging.basicConfig(level=logging.INFO)

prompt_template_generate_script = os.path.join(os.path.dirname(__file__), '..', 'prompt_templates', 'storytelling_script.yaml')

class StoryTellingEngine:
    def __init__(self):
        self.video_editor = VideoEditor()
        self.prompt_template_generate_script = None
        self.load_prompt_templates()

    def load_prompt_templates(self):
        with open(prompt_template_generate_script, 'r') as file:
            self.prompt_template_generate_script = yaml.safe_load(file)

    async def generate_video(self, is_instructions:bool, script:str = None, instructions:str = None):
        if script and len(script) > 1300:
            logging.error("The video script should not be longer than 1300 characters.")
            return {"status": "error", "message": "The video script should not be longer than 1300 characters."}

        if is_instructions:
            script = await self.video_editor.generate_script(instructions, self.prompt_template_generate_script)
            script = script["text_script"]

        scenes = await self.video_editor.create_scenes_from_script(script)
        script_summary = await self.video_editor.gpt_summary_of_script(script)

        json_data = {
            "images": [],
            "script": [],
            "extra_args": {
                "resolution": {
                    "width": 540,
                    "height": 960
                },
                "captions": {
                    "enabled": True,
                }
            }
        }

        for index, scene in enumerate(scenes):
            scene_bg_image = {
                "image_id": f"image_{index}",
                "source_type": "prompt",
                "source_content": await self.video_editor.gpt_image_prompt_from_scene(scene, script_summary),
                "start_time": f"scr_{index}.start_time",
                "end_time": f"scr_{index}.end_time",
                "max_width": "full",
                "max_height": "full",
                "z_index": 1,
                "position": [50, 50],
                "opacity": 1.0,
                "rotation": 0
            }

            json_data["images"].append(scene_bg_image)

            scene_script = {
                "_id": f"scr_{index}",
                "text": scene,
                "voice_start_time": 0
            }

            json_data["script"].append(scene_script)
            
        json2video = PyJson2Video(json_data, os.path.join(os.path.dirname(__file__), '..', 'result', f'storytelling_video_{uuid.uuid4()}.mp4'))
        output_video_path = await json2video.convert()

        return output_video_path