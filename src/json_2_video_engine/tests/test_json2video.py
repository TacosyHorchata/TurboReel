import sys
import os
import asyncio
import json

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.json_2_video_engine.json_2_video import PyJson2Video

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Load JSON data
template_json = load_json(f"{os.path.abspath(os.path.dirname(__file__))}/json2video_template_clean.json")
documentary_json = load_json(f"{os.path.abspath(os.path.dirname(__file__))}/json2video_documentary.json")

# Create PyJson2Video instances
json2video_template = PyJson2Video(
    template_json, 
    f"{os.path.abspath(os.path.dirname(__file__))}/output_template_clean.mp4"
)
json2video_documentary = PyJson2Video(
    documentary_json, 
    f"{os.path.abspath(os.path.dirname(__file__))}/output_documentary.mp4"
)

# Run desired json2video template
async def main():
    await json2video_documentary.convert()

if __name__ == "__main__":
    asyncio.run(main())
