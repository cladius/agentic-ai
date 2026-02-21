# Goal

Create a wordsearch solver using Langflow to hone your Agentic AI design and Langflow development skills.

# Problem

Parse an image of a word search puzzle and create HTML-based visualization of the solution. 
Details of the problem's genesis are documented [here](https://www.linkedin.com/pulse/blinkit-rescue-cladius-fernando-n52uc/).

# Obstacles

- Langflow does NOT provide a way to directly send an image to a LLM component.
- LLMs are bad (for the time being at least) at going through a letter grid to determine the exact positions of words in it.
- In case you are using Groq as an inference provider, the out-of-the-box component is NOT loading all the available models.

# Suggestions

- Follow the [design aids](https://github.com/cladius/agentic-ai/tree/master/design-aids) to break down the problem into smaller tasks.
- Use a custom component based on Groq component but enhance it to support Base64 input to handle the image data.
- Use a custom component to read from an "online" image rather than an uploaded image. For instance, you can read from this [url](https://www.rd.com/wp-content/uploads/2020/04/house_wordsearch-scaled.jpg)
<img width="2560" height="2560" alt="image" src="https://github.com/user-attachments/assets/935ad462-1de0-406c-a9de-1a5a7e20437f" />
- Use a custom component to solve the wordsearch aspect using Python code rather than rely on a LLM
- Tweak the source code of the Groq component to use a better model.

# Sample input in Langflow playground

```
Find the words windowsill, Drainpipe, hollowpipe, studio, bathroom , Chimney, foundations,
garage, turret, hatrack, well, arcade, bedroom, ceiling, shutter, patio, stove, fireescape,
drainpipe, corridor, hollowwall, floor, dormerwindow, office, kitchen, colonnade, sittingarea,
bedstead, doorstep, shutter, wallanchor, gutter
```

# Sample (truncated) output in Langflow playground

<img width="833" height="413" alt="Screenshot 2026-02-16 at 23 43 14" src="https://github.com/user-attachments/assets/394dfd22-0564-4bf4-b687-855794be103e" />

# Sample output rendered in browser for above HTML

<img width="693" height="770" alt="image" src="https://github.com/user-attachments/assets/5e9cbe49-3424-44b2-80f2-54d4320d70ad" />

# Hint 1

Create a custom component that reads an image URL as **Input** and provides the base64 data portion of it as **Output**.

<details>
<summary>Code Snippet</summary>

  ```python
  
from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data
from langflow.schema.message import Message
import requests
import base64
from io import BytesIO


class ImageURLToBase64(Component):
    display_name = "Image URL to Base64"
    description = "Fetches an image from a URL and converts it to base64 format"
    icon = "image"
    
    inputs = [
        MessageTextInput(
            name="image_url",
            display_name="Image URL",
            info="URL or local file path of the image (PNG, JPG, etc.)",
            required=True,
        ),
    ]
    
    outputs = [
        Output(display_name="Base64 Message", name="base64_message", method="get_base64_message")
    ]
    
    def convert_image(self) -> Data:
        """Convert image from URL to base64"""
        try:
            image_url = self.image_url

            # FILL IN THE BLANKS. ADD YOUR LOGIC HERE
            
            # Convert to base64
            base64_string = base64.b64encode(image_data).decode('utf-8')
            
            # Create data object with both base64 and metadata
            result = Data(
                data={
                    "base64": base64_string,
                    "content_type": content_type,
                    "data_url": f"data:{content_type};base64,{base64_string}"
                }
            )
            
            self.status = f"Successfully converted image from {image_url}"
            return result
            
        except requests.exceptions.RequestException as e:
            self.status = f"Error fetching image: {str(e)}"
            raise Exception(f"Failed to fetch image from URL: {str(e)}")
        except FileNotFoundError as e:
            self.status = f"File not found: {str(e)}"
            raise Exception(f"Local file not found: {str(e)}")
        except Exception as e:
            self.status = f"Error: {str(e)}"
            raise Exception(f"Failed to convert image: {str(e)}")
    
    def get_base64_message(self) -> Message:
        """Return base64 string as a Message object"""
        result = self.convert_image()
        base64_str = result.data.get("base64", "")
        return Message(text=base64_str)
    
```

</details>

# Hint 2

Create a custom component that reads a 2D letter grid AND words to be found as **Input**, finds the words in the grid and 
returns a HTML visualization of it as **Output**.

<details>
<summary>Code Snippet</summary>

  ```python

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data, Message
import json


class WordGridFinderComponent(Component):
    display_name = "Word Grid Finder"
    description = "Finds words in a 2D letter grid and generates HTML visualization"
    icon = "grid-3x3"

    inputs = [
        MessageTextInput(
            name="grid_json",
            display_name="Letter Grid (JSON)",
            info="2D array of letters as JSON string",
            value='[["S","T","U","D","I","O","L","B","A","T","H","R","O","O","M"],["C","A","N","H","O","L","L","O","W","W","A","L","L","A","T"]]'
        ),
        MessageTextInput(
            name="word_list",
            display_name="Word List",
            info="Comma-separated list of words to find",
            value="STUDIO, BATHROOM, HOLLOW, WALL"
        ),
    ]

    outputs = [
        Output(type=Message, display_name="HTML", name="html_output", method="find_words"),
    ]

    def find_word_in_grid(self, grid, word):
        """Find a word in the grid in all 8 directions"""
        # FILL IN THE BLANKS. ADD YOUR LOGIC HERE
        return positions

    def find_words(self) -> Message:
        try:
            # Parse inputs
            grid = json.loads(self.grid_json)
            words = [w.strip().upper() for w in self.word_list.split(',')]
            
            # Find all words and their positions
            all_positions = {}
            found_words = []
            
            for word in words:
                positions = self.find_word_in_grid(grid, word)

            # FILL IN THE BLANKS. ADD YOUR LOGIC HERE
            
            # Generate HTML
            html = self.generate_html(grid, all_positions, found_words)
            
            return Message(text=html)
            
        except Exception as e:
            error_html = f"<div style='color: red;'>Error: {str(e)}</div>"
            return Data(data={"html": error_html, "found_words": []})

    def generate_html(self, grid, positions_dict, found_words):
        """Generate HTML visualization of the grid"""
        # Create a set of all highlighted positions
        highlighted = set()
        for positions in positions_dict.values():
            highlighted.update(positions)
        
        html = """
        # FILL IN THE BLANKS. ADD YOUR LOGIC HERE
        """
        
        return html
  ```

    
</details>


# Hint 3
Create a custom component that will take input as base64 data and then make a call to Groq. Keep it similar to the OOTB Groq component.

<details>
<summary>Code Snippet</summary>

  ```python


from langflow.custom import Component
from langflow.inputs import StrInput, SecretStrInput, MessageTextInput, DropdownInput
from langflow.io import Output
from langflow.schema import Data, Message
from groq import Groq
import base64


class GroqVisionBase64Component(Component):
    display_name = "Groq Vision (Base64)"
    description = "Send base64 image data to Groq's multimodal models"
    documentation = "https://console.groq.com/docs/vision"
    icon = "Groq"
    
    inputs = [
        SecretStrInput(
            name="groq_api_key",
            display_name="Groq API Key",
            required=True,
            info="Your Groq API key from https://console.groq.com"
        ),
        MessageTextInput(
            name="base64_image",
            display_name="Base64 Image Data",
            required=True,
            info="Base64 encoded image data (can include data URI prefix or just the base64 string)"
        ),
        MessageTextInput(
            name="prompt",
            display_name="Text Prompt",
            required=True,
            info="Your question or instruction about the image"
        ),
        DropdownInput(
            name="model",
            display_name="Model",
            options=[
                "llama-3.2-90b-vision-preview",
                "llama-3.2-11b-vision-preview",
                "meta-llama/llama-4-maverick-17b-128e-instruct"
            ],
            value="llama-3.2-90b-vision-preview",
            info="Groq vision model to use"
        ),
        DropdownInput(
            name="image_type",
            display_name="Image Type",
            options=[
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp"
            ],
            value="image/jpeg",
            info="MIME type of the image"
        )
    ]
    
    outputs = [
        Output(type=Message, display_name="Response", name="response", method="process_image"),
    ]
    
    def process_image(self) -> Message:
        try:
            # Initialize Groq client
            client = Groq(api_key=self.groq_api_key)
            
            # Clean the base64 data
            base64_data = self.base64_image.strip()
            
            # Remove data URI prefix if present
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[1]
            
            # Construct the image URL for Groq API
            image_url = f"data:{self.image_type};base64,{base64_data}"
            
            # Create the messages payload
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ]
            
            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=self.model
            )
            
            # Extract response
            response_text = chat_completion.choices[0].message.content
            
            return Message(text=response_text)
            
        except Exception as e:
            error_msg = f"Error processing image with Groq: {str(e)}"
            self.log(error_msg)
            return Data(
                data={
                    "response": error_msg,
                    "error": True
                }
            )
```
</details>
