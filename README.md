# TurboReelGPT

**Welcome to TurboReelGPT!** Your new buddy for creating short videos for TikTok, Instagram Reels, and YouTube Shorts. Unlike other AI video generators out there, we’re all about making your content feel real.

## What We're About

Just like Midjourney changed the game for images, TurboReelGPT is here to transform how we make videos. Our mission is to help creators easily produce videos that connect with their audience on a human level.

- **Check This Out**: Want to see what you can create? Check out this [example video](https://youtu.be/4tFtKmXc-xE?si=KTb0MLfAYTe7eVtP).
![Video Preview](https://i.ytimg.com/vi/4tFtKmXc-xE/hqdefault.jpg)

## 🚀 Our Roadmap

1. **Storytelling**: Work on improving how we tell stories in videos.
2. **Stock Images Galore**: Add more stock images for users to choose from.
3. **More Voice Options**: Introduce even more human-like voice choices.
4. **AI-Generated Images**: Let users create and use AI-generated images in their videos.
5. **Bring in Human Avatars**: Develop realistic avatars for users to include in their videos.
6. **Animate Away**: Add more animations to keep videos exciting.
7. **AI for Image Recognition**: Use AI to recognize images and sync them better with videos.
8. **Fun Video Remixing**: Let users remix and play around with existing videos.

## 💡 Getting Started

Ready to dive in? Here’s how to get started with TurboReelGPT:

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/yourusername/turboreelgpt.git
   ```

2. **Head to the Project Folder**:
   ```bash
   cd turboreelgpt
   ```

3. **Make Sure You’ve Got Python**: Grab Python 3.10.x from [python.org](https://www.python.org/downloads/release/python-31012/).

4. **Install FFmpeg and ImageMagick**:
   - **For Windows**: Download the binaries from [FFmpeg](https://ffmpeg.org/download.html) and [ImageMagick](https://imagemagick.org/script/download.php). Just add them to your system's PATH.
   - **For macOS**: Use Homebrew (if you haven’t tried it yet, now’s the time!):
     ```bash
     brew install ffmpeg imagemagick
     ```
   - **For Linux**: Just use your package manager:
     ```bash
     sudo apt-get install ffmpeg imagemagick
     ```

5. **Get the Required Python Packages**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Grab Your API Keys**: You’ll need keys for OPENAI (for generating scripts) and PEXELS (for fetching images). Get your PEXELS API key [here](https://www.pexels.com/api/key/).

7. **Set Up Your Config**: Create a `config.yaml` file in the root folder. Clone `config-example.yaml` and fill it in with your API keys and desired settings. You only need to configure settings other than the API keys if you're not using the Gradio UI.

8. **Gradio UI**: Run:
   ```bash
   python3 GUI.py
   ```
Fill in all the inputs and generate your video!

![GUI Preview](https://cdn.discordapp.com/attachments/1286824377949884535/1294179188642938901/image.png)

   **Heads Up**: This project uses YT-DLP for downloading YouTube videos, and it requires cookies to work properly. Automating this in a VM might not be the best idea.
   
## 🤗 Want to Help?

We’d love your help! If you’re excited to contribute to TurboReelGPT, here’s how you can jump in:

1. **Fork the Repo**.
2. **Create a New Branch** for your feature or fix.
3. **Make Your Changes and Commit Them**.
4. **Push Your Branch** and submit a pull request.

- **Join Our Crew**: Let’s connect! Join us and other creators on our [Discord server](https://discord.gg/bby6DYsCPu). We can’t wait to see what you create!
