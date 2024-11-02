import json
import os
import logging
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
reference_json_path = os.path.join(os.path.dirname(__file__), '..', 'json_templates', 'json2video_storytelling.json')

def json_raw_generation(reference_json: dict, instructions: str, elements_to_include: list = None):
    elements_to_include = elements_to_include or []
    
    messages = [
            {"role": "system", "content": f"""You are an AI assistant that generates JSON structures for video creation based on user instructions. 
            Use the provided reference JSON as a template. 
            Focus on the following key points:
                1. Generate a script that is at least 120-140 words long and video has at least 3 images.
                2. Always synchronize image timings with the script by using dynamic references:
                    - For start times: use ["script_id"].start_time or ["script_id"].voice_start_time
                    - For end times: use ["script_id"].end_time or ["script_id"].voice_end_time
                3. Ensure the JSON structure includes images, and script elements, text elements are optional.
                4. If elements_to_include is not empty, include one or more of the elements in the JSON structure, as you see fit. 
                Elements is an array of dictionaries with the following structure: path and description.
                Elements to include:\n\n{json.dumps(elements_to_include, indent=2)}   
                5. source_type should be either prompt or path. Path should only be included if the path is in the elements_to_include array.
                
                Reference JSON structure for a video:\n\n{json.dumps(reference_json, indent=2)}
                
            """},
            {"role": "user", "content": f"Please generate a similar JSON structure based on the following instructions:\n\n{instructions}"}
        ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=messages,
        max_tokens=2000,
        n=1,
        temperature=0.2,
        response_format={"type": "json_object"}  # Ensure JSON response
        )

    generated_json = json.loads(response.choices[0].message.content)

    return generated_json

def json_verification(reference_json: dict, generated_json: dict, elements_to_include: list = []):
    parsed_json = json.loads(generated_json) if isinstance(generated_json, str) else generated_json

    instructions = f"""Instructions:
    1. Ensure all required elements (images, text(optional), script) are present.
    2. Verify that the timing is correct and synchronized.
    3. Check that image and text timings use script_id references (e.g., 'script_id.start_time', 'script_id.end_time') instead of hard-coded numbers.
    4. Validate that the script is at least 120-140 words long and video has at least 3 images.
    5. Check that the elements_to_include paths are the same as the ones in the JSON structure. This is very important, since the paths will be used to get the element.
    Elements to include:\n\n{json.dumps(elements_to_include, indent=2)}
    6. source_type should be either prompt or path. Path should only be included if the path is in the elements_to_include array.

    In case something is not correct, please fix it. And return the corrected JSON structure.
    """

    prompt = f"""
    Reference JSON structure:\n{json.dumps(reference_json, indent=2)}
    JSON structure to verify:\n{json.dumps(parsed_json, indent=2)}
    """

    verification = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": f"You are an AI assistant specialized in verifying JSON structures for a video creation engine that uses a static JSON structure(images, text, script). \n {instructions}"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=2000,
        n=1,
        temperature=0.2,
        )
        
    verification_result = json.loads(verification.choices[0].message.content)

    return verification_result

def generate_json_for_video(instructions: str, elements_to_include: list = None):
    with open(reference_json_path, 'r') as file:
        reference_json = json.load(file)

    generated_json = json_raw_generation(reference_json, instructions, elements_to_include)
    verified_json = json_verification(reference_json, generated_json, elements_to_include)

    return verified_json


""" ## test

instructions = "story about how the oppenheimer movie was made"
#elements_to_include = [{"element_id": "image_1", "description": "A picture of a cat"}, {"element_id": "image_2", "description": "A picture of a dog"}]

print(generate_json_for_video(instructions)) """