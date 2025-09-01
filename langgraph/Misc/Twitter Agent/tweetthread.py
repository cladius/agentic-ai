"""
LangGraph Implementation for Daily Ebook Sharing to X/Twitter

This implementation:
1. Reads a PDF ebook and extracts a random page within a specified range
2. Takes a screenshot of that page
3. Uses Groq LLM to generate a social media post based on the page content
4. Posts the content and image to X (Twitter)
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, TypedDict, Literal
from langgraph.graph import StateGraph, END
import time as sleep_time
import fitz 
import requests
import tweepy  # For X API
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Type definitions for state management
class PageInfo(TypedDict):
    page_number: int
    image_path: str
    page_text: str
    
class PostDetails(TypedDict):
    content: str
    status: Literal["draft", "approved", "posted"]
    
class EbookSharerState(TypedDict):
    ebook_path: str
    page_range: Dict[str, int]  # {start: int, end: int}
    current_page_info: PageInfo
    post: PostDetails
    error: str

# Node implementations
def select_random_page(state: EbookSharerState) -> EbookSharerState:
    """Selects a random page from the ebook within the specified range."""
    try:
        # Open the PDF document
        doc = fitz.open(state["ebook_path"])
        
        # Select a random page within the range
        start_page = state["page_range"]["start"]
        end_page = min(state["page_range"]["end"], doc.page_count)
        random_page_num = random.randint(start_page, end_page)
        
        # Extract the page
        page = doc[random_page_num-1]  # 0-indexed
        
        # Extract text for context
        text = page.get_text()
        
        # Generate image path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = f"page_{random_page_num}_{timestamp}.png"
        
        # Render page to an image and save
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        pix.save(image_path)
        
        doc.close()
        
        # Update state
        state["current_page_info"] = {
            "page_number": random_page_num,
            "image_path": image_path,
            "page_text": text
        }
        state["error"] = ""
        
        print(f"Selected page {random_page_num} and saved as {image_path}")
        
    except Exception as e:
        state["error"] = f"Error selecting random page: {str(e)}"
        print(state["error"])
    
    return state

def generate_post_with_groq(state: EbookSharerState) -> EbookSharerState:
    """Sends the page screenshot to Groq and asks it to create a post."""
    try:
        if state["error"]:
            return state

        # Get Groq API key from environment
        groq_api_key = os.getenv("GROQ_API_KEY")
        groq_api_url = os.getenv("GROQ_API_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")

        # Prepare the prompt for Groq
        prompt = f"""
        This is a page from my book Excellence: Bridging the gap between classroom and cubicle (page {state['current_page_info']['page_number']}). 
        Please create a short, engaging, semi-informal post for X (Twitter) that highlights the wisdom from this page. This post will be shared from my X account.
        The post should be concise (under 280 characters), thought-provoking, and include relevant hashtags The relevant audience is budding software engineers.

        Here's the text from the page:
        {state['current_page_info']['page_text']}
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {groq_api_key}"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",  # Example Groq model, update as needed
            "messages": [
                {"role": "system", "content": "You are an expert at creating engaging social media content."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        # Make the API call
        response = requests.post(groq_api_url, headers=headers, json=payload)
        response_data = response.json()
        post_content = response_data["choices"][0]["message"]["content"]

        # Update state
        state["post"] = {
            "content": post_content,
            "status": "draft"
        }

        print(f"Generated post: {post_content}")

    except Exception as e:
        state["error"] = f"Error generating post with Groq: {str(e)}"
        print(state["error"])

    return state

def get_twitter_auth():
    """Fetch Twitter credentials from .env and return Tweepy clients (v2 and v1.1)."""
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise EnvironmentError("Missing one or more required Twitter API credentials.")

    # Initialize OAuth1.0a for media upload
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)

    # Initialize OAuth1.0a client for Tweeting
    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
        wait_on_rate_limit=True
    )

    return client_v2, api_v1

def post_to_x(state: EbookSharerState) -> EbookSharerState:
    """Posts content and image to X (Twitter) using v2 client and v1.1 media upload."""
    try:
        if state.get("error"):
            return state

        client, api = get_twitter_auth()

        # Upload media (required via v1.1)
        image_path = state["current_page_info"]["image_path"]
        media = api.media_upload(filename=image_path)

        # Create tweet with media
        tweet_text = state["post"]["content"]
        response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])

        tweet_id = response.data.get("id")
        print(f"✅ Successfully posted to X with tweet ID: {tweet_id}")

        state["post"]["status"] = "posted"

        # ➕ Post reply tweet
        reply_text = "Excel at the art that is software engineering! Get a mentor in print format. Invest in yourself. https://cladiusfernando.com/excellence/"
        
        # Upload cover image for reply
        cover_image_path = "/Users/demo/Code/CMO/Cover.jpeg"
        cover_media = api.media_upload(filename=cover_image_path)
        
        reply = client.create_tweet(
            text=reply_text,
            media_ids=[cover_media.media_id],
            in_reply_to_tweet_id=tweet_id
        )
        reply_id = reply.data.get("id")
        print(f"💬 Posted reply tweet with ID: {reply_id}")

        # Optional: clean up image file
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"🧹 Deleted image file: {image_path}")

    except tweepy.TweepyException as e:
        state["error"] = f"Twitter API error: {str(e)}"
        print(state["error"])
    except Exception as e:
        state["error"] = f"Error posting to X: {str(e)}"
        print(state["error"])

    return state

def handle_error(state: EbookSharerState) -> Literal["retry", "end"]:
    """Error handling logic to determine next steps."""
    if state["error"]:
        print(f"Error encountered: {state['error']}")
        # For certain errors, we might want to retry
        if "connection" in state["error"].lower() or "timeout" in state["error"].lower():
            print("Will retry in 5 minutes")
            sleep_time.sleep(300)  # Wait 5 minutes
            return "retry"
        else:
            return "end"
    return "end"

# Build the LangGraph
def build_ebook_sharing_graph(ebook_path: str, start_page: int, end_page: int) -> StateGraph:
    """Builds the LangGraph for the ebook sharing process."""
    
    # Initialize the graph
    graph = StateGraph(EbookSharerState)
    
    # Set up the initial state
    initial_state = EbookSharerState(
        ebook_path=ebook_path,
        page_range={"start": start_page, "end": end_page},
        current_page_info={"page_number": 0, "image_path": "", "page_text": ""},
        post={"content": "", "status": "draft"},
        error=""
    )
    
    # Add nodes
    graph.add_node("select_random_page", select_random_page)
    graph.add_node("generate_post", generate_post_with_groq)
    graph.add_node("post_to_x", post_to_x)
    
    # Add edges
    graph.add_edge("select_random_page", "generate_post")
    graph.add_edge("generate_post", "post_to_x")
    graph.add_edge("post_to_x", END)
    
    # Add error handling
    graph.add_conditional_edges(
        "select_random_page",
        handle_error,
        {
            "retry": "select_random_page",
            "end": END
        }
    )
    
    graph.add_conditional_edges(
        "generate_post",
        handle_error,
        {
            "retry": "generate_post",
            "end": END
        }
    )
    
    graph.add_conditional_edges(
        "post_to_x",
        handle_error,
        {
            "retry": "post_to_x",
            "end": END
        }
    )
    
    # Set the entry point
    graph.set_entry_point("select_random_page")
    
    return graph.compile()

def run_once_for_testing(ebook_path: str, start_page: int, end_page: int):
    """Run the graph once for testing purposes."""
    graph = build_ebook_sharing_graph(ebook_path, start_page, end_page)
    
    # Create initial state
    state = EbookSharerState(
        ebook_path=ebook_path,
        page_range={"start": start_page, "end": end_page},
        current_page_info={"page_number": 0, "image_path": "", "page_text": ""},
        post={"content": "", "status": "draft"},
        error=""
    )
    
    # Run the graph
    final_state = graph.invoke(state)
    print("Final state:", json.dumps(final_state, indent=2))
    
    return final_state

run_once_for_testing("/Users/demo/Code/CMO/Excellence.pdf", 9, 268)

