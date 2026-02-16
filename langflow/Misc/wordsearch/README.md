# Goal

Create a wordsearch solver using Langflow to hone your Agentic AI design and Langflow development skills.

# Problem

Parse an image of a word search puzzle and create HTML-based visualization of the solution. 
Details of the problem's genesis are documented [here](https://www.linkedin.com/pulse/blinkit-rescue-cladius-fernando-n52uc/).

# Obstacles

- Langflow does NOT provide a way to directly send an image to a LLM component.
- LLMs are bad (for the time being at least) at going through a letter grid to determine the exact positions of words in it.

# Suggestions

- Follow the [design aids](https://github.com/cladius/agentic-ai/tree/master/design-aids) to break down the problem into smaller tasks.
- Use a custom component based on Groq component but enhance it to support Base64 input to handle the image data.
- Use a custom component to read from an "online" image rather than an uploaded image. For instance, you can read from this [url](https://www.rd.com/wp-content/uploads/2020/04/house_wordsearch-scaled.jpg)
<img width="2560" height="2560" alt="image" src="https://github.com/user-attachments/assets/935ad462-1de0-406c-a9de-1a5a7e20437f" />
- Use a custom component to solve the wordsearch aspect using Python code rather than rely on a LLM

# Sample Solution Output

<img width="693" height="770" alt="image" src="https://github.com/user-attachments/assets/5e9cbe49-3424-44b2-80f2-54d4320d70ad" />
