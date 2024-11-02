import requests
import pysrt  
import logging
import os
import re
from openai import OpenAI 
import math
import time

from dotenv import load_dotenv  # To load environment variables

# Load environment variables from .env file
load_dotenv()

class ImageHandler:
    def __init__(self, pexels_api_key, openai_api_key):
        self.pexels_api_key = pexels_api_key
        self.openai_api_key = openai_api_key
        self.pixabay_api_key = os.getenv('PIXABAY_API_KEY') or ''
        self.openai = OpenAI(api_key=self.openai_api_key)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def generate_image_pollinations(self, query, width=1024, height=1024, model=None, seed=None, nologo=False, private=True, enhance=False, timeout=15):
        """Generate an image using Pollinations AI API
        
        Args:
            query (str): Text description of the image to generate
            width (int, optional): Width of generated image. Defaults to 1024
            height (int, optional): Height of generated image. Defaults to 1024
            model (str, optional): Model to use for generation
            seed (int, optional): Seed for reproducible results
            nologo (bool, optional): Turn off logo rendering. Defaults to False
            private (bool, optional): Prevent image from appearing in public feed. Defaults to True
            enhance (bool, optional): Enable prompt enhancing via LLM. Defaults to False
            timeout (int, optional): Maximum time to wait for image generation in seconds. Defaults to 15
        
        Returns:
            list: List containing the generated image URL if successful, empty list otherwise
        """
        # Build query parameters
        params = {
            'width': width,
            'height': height,
            'nologo': str(nologo).lower(),
            'private': str(private).lower(),
            'enhance': str(enhance).lower()
        }
        if model:
            params['model'] = model
        if seed is not None:
            params['seed'] = seed

        # URL encode the prompt
        encoded_query = requests.utils.quote(query)
        generate_url = f"https://image.pollinations.ai/prompt/{encoded_query}"

        try:
            full_url = requests.Request('GET', generate_url, params=params).prepare().url
            response = requests.get(full_url, timeout=timeout)
            if response.status_code == 200:
                return [full_url]
            return []
        except Exception as e:
            logging.error(f"Error generating image URL: {e}")
            return []

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

    def search_pixabay_images(self, query):
        """Search for images using Pixabay API and return the URLs."""
        search_url = "https://pixabay.com/api/"
        
        params = {
            'key': self.pixabay_api_key,
            'q': query,
            'image_type': 'all',
            'per_page': 3
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
        image_urls = [hit['largeImageURL'] for hit in search_results.get('hits', [])]  # Extract image URLs
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

        image_urls = [item['link'] for item in search_results.get('items', [])]  # Extract image URLs
        return image_urls

    def download_image(self, url, filename):
        """Download an image from a URL."""
        try:
            response = requests.get(url, timeout=10)  # Timeout for network issues
            response.raise_for_status()  # Raise for HTTP errors
            
            # Use absolute path for saving images
            assets_dir = os.path.join(self.base_dir, '..', 'assets', 'images')
            os.makedirs(assets_dir, exist_ok=True)  # Ensure directory exists
            
            full_path = os.path.join(assets_dir, filename)
            with open(full_path, 'wb') as f:
                f.write(response.content)
            return full_path
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download image: {e}")
        except Exception as e:
            logging.error(f"Error while saving image: {e}")
        return None

    def extract_keywords_from_subtitles(self, subtitles_file, video_duration):
        """Extract key phrases from subtitles based on video duration."""
        seconds_per_keyword = 5
        try:
            subs = pysrt.open(subtitles_file)
            keywords = []
            current_text = []
            
            # Calculate the number of keywords we should extract
            num_keywords = math.ceil(video_duration / seconds_per_keyword)
            
            # Calculate the duration for each keyword
            duration_per_keyword = video_duration / num_keywords
            
            current_duration = 0
            keyword_end_time = duration_per_keyword
            
            for sub in subs:
                if sub.start.seconds < keyword_end_time:
                    current_text.append(sub.text)
                else:
                    keywords.append(' '.join(current_text))
                    current_text = [sub.text]
                    keyword_end_time += duration_per_keyword

            # Add any remaining text as the last keyword
            if current_text:
                keywords.append(' '.join(current_text))
            
            logging.info(f"Extracted {len(keywords)} keywords from subtitles.")
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

    def get_images_from_subtitles(self, subtitles_file_path, video_context, video_duration):
        """Fetch relevant images based on the subtitles and video duration."""
        keywords = self.extract_keywords_from_subtitles(subtitles_file_path, video_duration)
        image_paths = []

        for keyword in keywords:
            try:
                refined_keyword = self.refine_keyword_with_openai(keyword, video_context)
            except Exception as e:
                logging.error(f"Error refining keyword: {keyword}")
                refined_keyword = keyword  # Use original keyword if refinement fails

            logging.info(f"Searching image for keywords: {refined_keyword}")

            try:
                ## Search for images using first Pollinations API
                image_urls = self.generate_image_pollinations(refined_keyword)
                if not image_urls:
                    ## Search for images using Pexels API
                    image_urls = self.search_pexels_images(refined_keyword)
                    if not image_urls:
                        ## Search for images using Pixabay API
                        image_urls = self.search_pixabay_images(refined_keyword)
                    logging.info(f"No images found on Pexels, searching on Pixabay: {image_urls}")
                if not image_urls:
                    logging.info(f"No images found on Pixabay")
            except Exception as e:
                logging.error(f"Error searching for images: {e}")
                image_paths.append(None)  # Add None for failed image search
                continue

            if image_urls:
                refined_keyword = re.sub(r'[^a-zA-Z0-9_]', '', refined_keyword.replace(' ', '_').replace('"', ''))
                img_filename = f"subtitle_image_{refined_keyword}.jpg"
                logging.info(f"Downloading image: {image_urls[0]}")
                downloaded_path = self.download_image(image_urls[0], img_filename)
                if downloaded_path:
                    image_paths.append(downloaded_path)
                else:
                    image_paths.append(None)  # Add None for failed download
            else:
                image_paths.append(None)  # Add None if no image URLs found

        return image_paths
