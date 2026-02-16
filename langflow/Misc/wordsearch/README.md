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

