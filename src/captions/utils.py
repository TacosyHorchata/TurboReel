import pysrt

def convert_seconds_to_srt_time(seconds):
    """Convert seconds into SubRipTime for SRT formatting"""
    millis = int((seconds % 1) * 1000)
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return pysrt.SubRipTime(hours, mins, secs, millis)
