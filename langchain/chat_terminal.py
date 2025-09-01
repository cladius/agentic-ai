from langchain_groq import ChatGroq
from langchain.schema import HumanMessage
from config import Config

# Optionally load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = Config.GROQ_API_KEY
MODEL_NAME = Config.MODEL_NAME

llm = ChatGroq(
    groq_api_key=API_KEY,
    model_name=MODEL_NAME
)

def chat():
    print("Welcome to LangChain Groq Chat! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        response = llm([HumanMessage(content=user_input)])
        print(f"AI: {response.content}")

if __name__ == "__main__":
    chat()
