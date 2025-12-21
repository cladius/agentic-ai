
# **LEVEL 5**
 **OBJECTIVE**\
 Create tools mimicking Google's NotebookLM. 
 Create an agent that generates mind maps or is capable of creating a 2-way podcast on any given topic.

 # **Mind Map Tool**
 Users enter prompts requesting mind maps to the agent. On receive the prompt the LLM (in this case gemini) is instructed to create the title and name of the nodes for the mind map. This serves as input to the mind map tool. To generate the mind map the tool uses Mermaid.js, which generates the mermaid script for the mind map. The script is rendered using puppeteer and a screenshot is saved locally, in the `.mastra/output/mindmaps` directory.

### **Challenges**
 The first challenge was to determine the order of operation of the tool. Since Mastra wouldn't render the mermaid script on the playground, I used puppeteer (which serves as a headless browser) to render it, screenshot it and download locally.

### Output Screenshots 

![Prompt](https://github.com/meghnamankotia/mastra-psl/blob/main/assets/Screenshot%202025-11-29%20155630.png)
![Mindmap](https://github.com/meghnamankotia/mastra-psl/blob/main/assets/Screenshot%202025-11-29%20155648.png)

 # **Podcast Tool**
 Users enter prompts requesting podcasts on any desired topic. Gemini creates a script, including dialogue for the host and the guest. This dialogue is sent as a single text input to the podcast tool. The tool separates the lines of the dialogue and uses Google's text-to-speech model to create each individual audio clip. The audio clips are joined together using the ffmpeg libraries to create the final podcast which can be found in `.mastra/output/podcasts`.

### **Challenges**
 The tool was initially going to use ElevenLabs API for tts. Since the dialogue was spliced into several sections, the API was being called repeatedly in a loop. This caused the usage to be flagged as suspicious. 
 
### Output demo

[Video demo](https://github.com/meghnamankotia/mastra-psl/blob/main/assets/14.11.2025_00.33.51_REC.mp4)
