# notebooklm_local.py
import os, json, re
from typing import List, Dict
from bs4 import BeautifulSoup
import requests

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from langchain.chains import RetrievalQA

from youtube_transcript_api import YouTubeTranscriptApi

EMBED_MODEL = "nomic-embed-text:latest"
LLM_MODEL = "llama3:latest"
INDEX_DIR = "faiss_index"

splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)

def load_pdf(path: str) -> List[Document]:
    return PyPDFLoader(path).load()

def load_web(url: str) -> List[Document]:
    html = requests.get(url, timeout=30).text
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    return [Document(page_content=text, metadata={"source": url})]

def extract_yt_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else ""

def load_youtube(url: str) -> List[Document]:
    vid = extract_yt_id(url)
    if not vid:
        return [Document(page_content="", metadata={"source": url, "error": "no id"})]
    segments = YouTubeTranscriptApi.get_transcript(vid, languages=["en"])
    text = " ".join(s["text"] for s in segments)
    return [Document(page_content=text, metadata={"source": url, "type": "youtube"})]

def load_text(name: str, text: str) -> List[Document]:
    return [Document(page_content=text, metadata={"source": name})]

def build_or_load_index(docs: List[Document]):
    chunks = splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    if os.path.exists(INDEX_DIR):
        db = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(chunks)
    else:
        db = FAISS.from_documents(chunks, embeddings)
    db.save_local(INDEX_DIR)
    return db

def retriever():
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    db = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    return db.as_retriever(search_type="mmr", search_kwargs={"k": 6, "fetch_k": 24, "lambda_mult": 0.6})

def rag_answer(question: str) -> str:
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever(), chain_type="stuff")
    out = qa.invoke({"query": question})
    return out.get("result", str(out))

def make_mindmap(topic: str, max_nodes: int = 20) -> Dict:
    # Ask LLM to produce a hierarchical JSON and a Mermaid mindmap
    llm = ChatOllama(model=LLM_MODEL, temperature=0.2)
    system = (
        "You generate concise mind maps from a corpus. "
        "Return JSON with {title, nodes:[{id,label,children:[...] }] } and ALSO a 'mermaid' string "
        "in mindmap syntax. Use <= {max_nodes} nodes total, labels under 6 words each. "
        "Ground ideas in retrieved context; if unsure, keep generic."
    ).replace("{max_nodes}", str(max_nodes))
    prompt = f"{system}\nCreate a mind map about: {topic}.\n"
    # Use RAG to gather context, then stuff into the prompt
    ctx = rag_answer(f"Summarize key concepts and topics for a mind-map about: {topic}. 120 bullets max.")
    resp = llm.invoke(f"{prompt}\nContext:\n{ctx}\nReturn JSON with keys: title,nodes,mermaid.")
    # naive JSON extraction
    text = resp.content if hasattr(resp, "content") else str(resp)
    try:
        js = json.loads(re.search(r"\{[\s\S]*\}", text).group(0))
    except Exception:
        js = {"title": topic, "nodes": [], "mermaid": "mindmap\n  root(({topic}))".replace("{topic}", topic)}
    return js

def podcast_script(topic: str, duration_min: int = 5) -> str:
    llm = ChatOllama(model=LLM_MODEL, temperature=0.3)
    ctx = rag_answer(f"Provide the main talking points and controversies about: {topic}.")
    prompt = (
        f"Write a two-host podcast script about '{topic}'.\n"
        f"Target length ~{duration_min} minutes. Hosts: Alex and Sam.\n"
        "Style: conversational, factual, cite insights from context where relevant.\n"
        "Include intro, 3-5 sections, and outro. Format as: HOST: line."
        f"\nContext:\n{ctx}\n"
    )
    return (llm.invoke(prompt).content)

def render_tts(script: str, out_wav="podcast.wav"):
    # local, simple TTS (Windows/mac uses system voice via pyttsx3)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(script, out_wav)
        engine.runAndWait()
        return out_wav
    except Exception as e:
        return f"TTS skipped: {e}"

if __name__ == "__main__":
    
    docs = []
    # docs += load_pdf("example.pdf") if os.path.exists("example.pdf") else []
    docs += load_web("https://en.wikipedia.org/wiki/Compiler")  # sample compiler book site
    #docs += load_youtube("https://www.youtube.com/watch?v=azcrPFhaY9k")  # sample CS talk
    # docs += load_text("pasteblock", "This dump includes exam AIR=152 and CGPA=8.71.")  # example paste

    if docs:
        build_or_load_index(docs)

    # 2) RAG Q&A
    print("\nQ&A:")
    print(rag_answer("What challenges commonly arise in compiler design?"))

    # 3) Mind map (NotebookLM-style)
    mm = make_mindmap("Challenges of compiler design", max_nodes=18)
    print("\nMind map JSON keys:", list(mm.keys()))
    # Save outputs
    with open("mindmap.json", "w", encoding="utf-8") as f:
        json.dump(mm, f, ensure_ascii=False, indent=2)
    if "mermaid" in mm:
        with open("mindmap.mmd", "w", encoding="utf-8") as f:
            f.write(mm["mermaid"])

    # 4) Podcast (script + optional audio)
    script = podcast_script("Challenges of compiler design", duration_min=6)
    with open("podcast_script.txt", "w", encoding="utf-8") as f:
        f.write(script)
    print("\nPodcast script saved to podcast_script.txt")
    print(render_tts(script))
