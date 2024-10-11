import gradio as gr
from src.generateVideo import generate_video
import asyncio
import os

def generate_video_wrapper(video_source, video_file, video_url, script_type, video_topic, video_script):
    video_path = video_file.name if video_file else None
    params = {
        "video_path_or_url": video_source,
        "video_path": video_path,
        "video_url": video_url,
        "video_topic": video_topic,
        "video_script": video_script,
        "video_script_type": script_type
    }
    result = asyncio.run(generate_video(**params))
    return str(result)

with gr.Blocks() as iface:
    with gr.Row():  # Added a row to position elements
        gr.Image("public/turboreel_logo.png", label="TurboReel Logo", width=200, height=50)
    gr.Markdown("Generate a video based on the provided parameters.")

    with gr.Row():
        video_source = gr.Radio(["video_path", "video_url"], label="Video Source")
        script_type = gr.Radio(["based_on_topic", "ready_made_script"], label="Video Script Type")

    with gr.Group():
        video_file = gr.File(label="Select File", visible=False, file_types=["video"])
        video_url = gr.Textbox(label="YouTube URL", visible=False)

    with gr.Group():
        video_topic = gr.Textbox(label="Video Topic", visible=False)
        video_script = gr.Textbox(label="Video Script", lines=5, visible=False)

    output = gr.Textbox(label="Result")
    submit_btn = gr.Button("Generate Video")

    def update_visibility(video_src, script_typ):
        return {
            video_file: gr.update(visible=video_src == "video_path"),
            video_url: gr.update(visible=video_src == "video_url"),
            video_topic: gr.update(visible=script_typ == "based_on_topic"),
            video_script: gr.update(visible=script_typ == "ready_made_script")
        }

    video_source.change(update_visibility, [video_source, script_type], [video_file, video_url, video_topic, video_script])
    script_type.change(update_visibility, [video_source, script_type], [video_file, video_url, video_topic, video_script])

    submit_btn.click(
        generate_video_wrapper,
        inputs=[video_source, video_file, video_url, script_type, video_topic, video_script],
        outputs=output
    )

if __name__ == "__main__":
    iface.launch()