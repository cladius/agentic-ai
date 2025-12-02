from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import os
import json

llm = ChatOllama(model='mistral')
 


MEMORY_FILE='chat_memory.json'


def memory_load():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: chat_memory.json is corrupted. Starting fresh.")
            return []
    return []


def save_memory(history):
    with open(MEMORY_FILE,'w') as f:
        json.dump(history, f, indent=2)

def format_messages(history):
    return "\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in history)



def main():
    print('Welcome to the agent powered by Ollama + langchain')
    message_history=memory_load()

    while True:
        question = input('You: ')
        if question.lower() in {'exit','quit'}:
            print('Saving Conversation...')
            save_memory(message_history)
            break
        
        message_history.append({"role":"user","content":question})

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Use the past conversation to respond."),
            ("user", "{history}\nUser: {question}")
        ])

        history_context=format_messages(message_history)

        chain = prompt | llm
        response = chain.invoke({
            "question": question,
            "history": history_context
        })
        print('AI: ', response.content)

        message_history.append({"role": "assistant", "content": response.content})
        save_memory(message_history)


if __name__== "__main__":
    main()