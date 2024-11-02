import gradio as gr
import json
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from src.json_2_video_engine.json_2_video import PyJson2Video  # Import the process_video function
import asyncio
import uuid

logging.basicConfig(level=logging.INFO)

load_dotenv()

# Load the reference JSON
with open('src/json_2_video/tests/json2video_template_clean.json', 'r') as f:
    reference_json = json.load(f)

# Initialize the OpenAI client
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_from_json(json_input):
    try:
        output_filename = f"output_{uuid.uuid4()}.mp4"
        output_path = os.path.join(os.path.abspath("result"), output_filename)
        pyjson2video = PyJson2Video(json_input, output_path)
        output_path = asyncio.run(pyjson2video.convert())
        return {"status": "success", "message": "Video generated successfully", "output_path": output_path}
    except Exception as e:
        return {"status": "error", "message": f"Error processing video: {str(e)}"}

def generate_and_process_video(instructions):
    try:
        messages = [
            {"role": "system", "content": f"""You are an AI assistant that generates JSON structures for video creation based on user instructions. Use the provided reference JSON as a template. Focus on the following key points:
                1. Generate a script that is at least 100 words long.
                2. Always synchronize image timings with the script by using dynamic references:
                    - For start times: use ["script_id"].start_time or ["script_id"].voice_start_time
                    - For end times: use ["script_id"].end_time or ["script_id"].voice_end_time
                3. Ensure the JSON structure includes images, text, and script elements.
                Reference JSON structure for a video:\n\n{json.dumps(reference_json, indent=2)}
            """},
            {"role": "user", "content": f"Please generate a similar JSON structure based on the following instructions:\n\n{instructions}"}
        ]

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=messages,
            max_tokens=2000,
            n=1,
            temperature=0.3,
            response_format={"type": "json_object"}  # Ensure JSON response
        )

        generated_json = json.loads(response.choices[0].message.content)
        verification = json_verification(generated_json)

        if verification["status"] == "corrected":
            generated_json = verification["data"]
        elif verification["status"] == "feedback":
            return None, verification["message"]

        output_filename = f"output_{uuid.uuid4()}.mp4"
        output_path = os.path.join(os.path.abspath("result"), output_filename)
        pyjson2video = PyJson2Video(generated_json, output_path)
        output_path = asyncio.run(pyjson2video.convert())
        
        return {"status": "success", "message": "Video generated successfully", "output_path": output_path}, json.dumps(generated_json, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"Error processing video: {str(e)}"}, None

def json_verification(json_data):
    try:
        parsed_json = json.loads(json_data) if isinstance(json_data, str) else json_data
        verification_prompt = f"""
        Please verify the following JSON structure for a video creation template:
        1. Ensure all required elements (images, text, script) are present.
        2. Verify that the timing is correct and synchronized.
        3. Check that image and text timings use script_id references (e.g., 'script_id.start_time', 'script_id.end_time') instead of hard-coded numbers.
        4. Validate that the script is at least 100 words long.
        Reference JSON structure:\n{json.dumps(reference_json, indent=2)}
        JSON structure to verify:\n{json.dumps(parsed_json, indent=2)}
        """

        verification = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are an AI assistant specialized in verifying JSON structures for video creation."},
                {"role": "user", "content": verification_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            n=1,
            temperature=0.3,
        )
        
        verification_result = json.loads(verification.choices[0].message.content)

        if verification_result["status"] == "corrected":
            return {"status": "corrected", "message": "JSON structure corrected.", "data": verification_result["data"]}
        else:
            return {"status": "feedback", "message": verification_result["message"]}
    except json.JSONDecodeError:
        return {"status": "error", "message": "Error: Input is not valid JSON. Please provide a valid JSON structure."}
    except Exception as e:
        return {"status": "error", "message": f"Error during verification: {str(e)}"}

def download_json_template():
    return json.dumps(reference_json, indent=2)

def process_result(result):
    if isinstance(result, str):
        try:
            result = eval(result)
        except:
            return {"status": "error", "message": result}, gr.update(visible=False), None

    if result["status"] == "success":
        output_message = f"Status: {result['status']}\nMessage: {result['message']}\nOutput Path: {result['output_path']}"
        return output_message, gr.update(visible=True), gr.update(value=result['output_path'], visible=True)
    else:
        return f"Status: {result['status']}\nMessage: {result['message']}", gr.update(visible=False), None

# Update the Gradio interface
with gr.Blocks() as iface:
    gr.Markdown("# Mind")
    gr.Markdown("Enter instructions for your video or provide a JSON structure directly. The AI will generate and process the video based on the input.")
    
    with gr.Tab("Text Instructions"):
        input_text = gr.Textbox(lines=5, label="Enter your video instructions")
        generate_button_text = gr.Button("Generate Video from Text", variant="primary")
        text_output = gr.Textbox(label="Result")
        video_output_text = gr.File(label="Download Generated Video", visible=False)
        json_output = gr.Textbox(label="JSON template or Error Message", lines=10)
    
    with gr.Tab("JSON Input"):
        json_input = gr.Textbox(lines=10, label="Enter your JSON structure directly")
        json_template = gr.File(label="JSON Template", file_count="single", file_types=[".json"])
        generate_button_json = gr.Button("Generate Video from JSON", variant="primary")
        json_output_result = gr.Textbox(label="Result")
        video_output_json = gr.File(label="Download Generated Video", visible=False)
    
    generate_button_text.click(
        generate_and_process_video, 
        inputs=[input_text], 
        outputs=[text_output, json_output]
    ).then(
        process_result,
        inputs=text_output,
        outputs=[text_output, generate_button_text, video_output_text]
    )

    generate_button_json.click(
        generate_from_json, 
        inputs=[json_input], 
        outputs=json_output_result
    ).then(
        process_result,
        inputs=json_output_result,
        outputs=[json_output_result, generate_button_json, video_output_json]
    )

# Launch the interface
iface.launch()
