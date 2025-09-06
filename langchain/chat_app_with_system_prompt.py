import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")

if not GROQ_API_KEY or not MODEL_NAME:
    print("Please set GROQ_API_KEY and MODEL_NAME in your .env file.")
    exit(1)

# Define a system prompt for the AI's behavior
SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer questions clearly and concisely." \
    "When asked to explain a concept, first give a clear definition, then provide a layman example, then provide a section with a list of related terms" \
    "For example, if asked about 'photosynthesis', first create a DEFINITION heading and say 'Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll.' "
    "Then create an EXAMPLE heading and say 'For example, a sunflower uses photosynthesis to convert sunlight into energy to grow and produce seeds.'" \
    "Finally, create a RELATED TERMS heading and list terms like 'chlorophyll', 'sunlight', and 'energy conversion'."
)

# Initialize Groq LLM (without system_prompt parameter)
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=MODEL_NAME,
    temperature=0.7  # Optional: control randomness
)

# Create a custom prompt template that includes the system prompt
prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Set up conversation chain with memory and custom prompt
conversation = ConversationChain(
    llm=llm,
    memory=ConversationBufferMemory(return_messages=True),
    prompt=prompt_template
)

def main():
    print("Welcome to the LangChain-Groq Chat Terminal!")
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        
        try:
            # Use invoke instead of run (modern LangChain method)
            response = conversation.invoke({"input": user_input})
            print(f"AI: {response['response']}")
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.")

if __name__ == "__main__":
    main()