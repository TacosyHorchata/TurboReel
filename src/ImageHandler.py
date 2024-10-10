import requests
import pysrt  
import logging
import os
import re
from openai import OpenAI 

from dotenv import load_dotenv  # To load environment variables

# Load environment variables from .env file
load_dotenv()

class ImageHandler:
    def __init__(self, pexels_api_key, openai_api_key):

        self.pexels_api_key = pexels_api_key
        self.openai_api_key = openai_api_key
        self.openai = OpenAI(api_key=self.openai_api_key)

    def search_pexels_images(self, query):
        """Search for images using Pexels API and return the URLs."""
        search_url = "https://api.pexels.com/v1/search"

        headers = {
            'Authorization': self.pexels_api_key
        }
        
        params = {
            'query': query,
            'per_page': 2
        }
        
        try:
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()  # Raise an error for bad responses
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")  # Log the error
            return []  # Return an empty list on error
        except Exception as e:
            logging.error(f"An error occurred during the request: {e}")
            return []

        search_results = response.json()
        image_urls = [photo['src']['original'] for photo in search_results.get('photos', [])]  # Extract image URLs
        return image_urls

    def search_google_images(self, query):
        """Search for images using Google Custom Search API and return the URLs."""
        search_url = "https://customsearch.googleapis.com/customsearch/v1?"
        
        params = {
            'q': query,
            'cx': self.google_cx,  # Ensure no leading/trailing spaces
            'searchType': 'image',
            'num': 1,  # Number of results to return
            'key': self.google_api_key.strip()  # Ensure no leading/trailing spaces
        }
        
        try:
            response = requests.get(search_url, params=params)
            response.raise_for_status()  # Raise an error for bad responses
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")  # Log the error
            return []  # Return an empty list on error
        except Exception as e:
            logging.error(f"An error occurred during the request: {e}")
            return []

        search_results = response.json()
        print(search_results)
        image_urls = [item['link'] for item in search_results.get('items', [])]  # Extract image URLs
        return image_urls

    def download_image(self, url, filename):
        """Download an image from a URL."""
        try:
            response = requests.get(url, timeout=10)  # Timeout for network issues
            response.raise_for_status()  # Raise for HTTP errors
            os.makedirs(os.path.dirname(filename), exist_ok=True)  # Ensure directory exists
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download image: {e}")
        except Exception as e:
            logging.error(f"Error while saving image: {e}")
        return None

    def extract_keywords_from_subtitles(self, subtitles_file):
        """Extract key phrases from subtitles."""
        seconds_per_keyword = 5
        try:
            subs = pysrt.open(subtitles_file)
            keywords = []
            current_text = []
            current_duration = 0
            
            for sub in subs:
                current_text.append(sub.text)
                current_duration += (sub.end - sub.start).milliseconds  # Use seconds attribute
                if current_duration >= seconds_per_keyword*1000:  # Check if we reached 5 seconds
                    keywords.append(' '.join(current_text))  # Join the accumulated text
                    current_text = []  # Reset for the next batch
                    current_duration = 0  # Reset duration
            
            return keywords
        except Exception as e:
            logging.error(f"Error extracting keywords from subtitles: {e}")
            return []

    def refine_keyword_with_openai(self, keyword, video_context):
        """Refine the keyword using OpenAI's ChatGPT 3.5 for better image search results."""

        try:
            completion = self.openai.chat.completions.create(  # Async call to create chat completion
                model="gpt-3.5-turbo",  # Updated model name
                temperature=0.25,
                messages = [
                    {
                        'role': 'system',
                        'content': 
                            '''You are a query generation system designed to enhance video automation. "
                            Your task is to take provided phrases and generate concise queries that will assist in finding appropriate images for the given scene.
                            Always produce a short, clear query based on the original phrase and the context of the video.
                            Example of ideal output: 'Sunset in California', 'Halloween costume', 'Friends meeting'.'''
                    },
                    {
                        'role': 'user',
                        'content': f'Original phrase: "{keyword}"\nVideo topic: {video_context}'
                    }
                ],
                max_tokens=200
            )
            refined_keyword = completion.choices[0].message.content.strip()
            return refined_keyword
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling OpenAI API: {e}")
            return keyword  # Return the original keyword on error

    def get_images_from_subtitles(self, subtitles_file_path, video_context):
        """Fetch relevant images based on the subtitles."""
        keywords = self.extract_keywords_from_subtitles(subtitles_file_path)  # Extract keywords from subtitles
        image_paths = []

        for keyword in keywords:

            try:
                refined_keyword = self.refine_keyword_with_openai(keyword, video_context)  # Refine the keyword
            except Exception as e:
                logging.error(f"Error refining keyword: {keyword}") 
                refined_keyword = ''  # Handle any exception that may occur

            logging.info(f"Searching image for keywords: {refined_keyword}")

            try:
                image_urls = self.search_pexels_images(refined_keyword)  # Search for images using the refined keyword
            except Exception as e:
                logging.error(f"Error searching for images: {e}")  # Log the error
                image_urls = None 

            if image_urls:
                
                # Replace spaces with underscores, remove double quotes, and filter out weird symbols
                refined_keyword = refined_keyword.replace(' ', '_')  # Replace spaces with underscores
                refined_keyword = refined_keyword.replace('"', '')   # Remove double quotes
                refined_keyword = re.sub(r'[^a-zA-Z0-9_]', '', refined_keyword)  # Remove weird symbols (keep alphanumeric and underscores)

                img_path = f"assets/images/subtitle_image_{refined_keyword}.jpg"
                logging.info(f"Downloading image: {image_urls[0]}")  # Unique filename for each image
                if self.download_image(image_urls[0], img_path):
                    image_paths.append(img_path)  # Add the downloaded image path to the list

        return image_paths