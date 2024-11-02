from moviepy.editor import TextClip, CompositeVideoClip
import pysrt
import logging
import os

class VideoCaptioner:
    def __init__(self):
        self.default_font = self.get_font_path("Dacherry.ttf")

    def get_font_path(self, font_name):
        # Look for the font in the 'fonts' directory within the project
        captions_root = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(captions_root, "fonts", font_name)
        if os.path.exists(font_path):
            return font_path
        else:
        
            logging.warning(f"Font file {font_name} not found. Using default system font.")
            return None

    def create_shadow_text(self, txt, fontsize, font, color, shadow_color, shadow_offset, blur_color, width):
        """ # Create the blurred shadow
        blur_size = int(fontsize * 1.08)  # 10% larger than the main text
        blur_clip = TextClip(txt, fontsize=blur_size, font=font, color=blur_color, size=(1000, None), method='caption')
        blur_clip = blur_clip.set_opacity(0.15)  # Set the opacity to 15%
         """
        
        # Create the offset shadow
        #shadow_clip = TextClip(txt, fontsize=fontsize, font=font, color=shadow_color, size=(width, None), method='caption')
        #shadow_clip = shadow_clip.set_position((shadow_offset, shadow_offset))

        # Create the main text
        text_clip = TextClip(txt, fontsize=fontsize*1.1, font=font, color=color, size=(width*0.8, None), method='caption', stroke_color=shadow_color, stroke_width=fontsize/15)
        
        # Composite all layers
        #return CompositeVideoClip([blur_clip, shadow_clip, text_clip])
        return CompositeVideoClip([text_clip])

    """ Call this function to generate the captions to video """
    def generate_captions_to_video(self, 
                                   subtitles_path,
                                   font=None, 
                                   captions_color='#BA4A00', 
                                   shadow_color='white',
                                   font_size=60,
                                   width=540
                                   ):
        font = self.get_font_path(font) if font else self.default_font
        try:
            subtitles = subtitles_path
            subtitle_clips = []
            shadow_offset = font_size / 10

            logging.info(f"Received subtitles: {type(subtitles)}")  # Debug log

            if isinstance(subtitles, str):
                # If subtitles is a string (file path), read the SRT file
                subtitles = pysrt.open(subtitles)
            elif isinstance(subtitles, list):
                # If subtitles is a list, assume it's a list of tuples (start, end, text)
                subtitles = [pysrt.SubRipItem(index=i, start=s, end=e, text=t) for i, (s, e, t) in enumerate(subtitles, 1)]

            if not isinstance(subtitles, (pysrt.SubRipFile, list)):
                raise ValueError(f"Unsupported subtitles format: {type(subtitles)}")

            for subtitle in subtitles:
                if isinstance(subtitle, pysrt.SubRipItem):
                    start_time, end_time, text = subtitle.start, subtitle.end, subtitle.text.upper()
                elif isinstance(subtitle, tuple) and len(subtitle) == 3:
                    start_time, end_time, text = subtitle
                    text = text.upper()
                else:
                    logging.warning(f"Skipping invalid subtitle format: {subtitle}")
                    continue

                shadow_text = self.create_shadow_text(
                    text, 
                    fontsize=font_size, 
                    font=font, 
                    color=captions_color, 
                    shadow_color=shadow_color, 
                    shadow_offset=shadow_offset,
                    blur_color='black',
                    width=width
                )
                
                start_seconds = start_time.ordinal / 1000 if hasattr(start_time, 'ordinal') else start_time
                end_seconds = end_time.ordinal / 1000 if hasattr(end_time, 'ordinal') else end_time
                duration = end_seconds - start_seconds
                
                subtitle_clip = (shadow_text
                                 .set_start(start_seconds)
                                 .set_duration(duration)
                                 .set_position(('center', 0.4), relative=True))
                subtitle_clips.append(subtitle_clip)

            logging.info(f"Generated {len(subtitle_clips)} subtitle clips")  # Debug log
            return subtitle_clips
        except Exception as e:
            logging.error(f"Error adding captions to video: {e}")
            logging.exception("Traceback:")  # This will log the full traceback
            return []
