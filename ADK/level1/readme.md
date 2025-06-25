

# 🤖 Programming Concepts Tutor using Google ADK + Gemini

This project is a Python-based CLI application that leverages **Google's Agent Development Kit (ADK)** and the **Gemini `gemini-2.0-flash` model** to create an interactive AI tutor. The agent is designed to provide **beginner-friendly explanations** of fundamental programming concepts such as:

* ✅ Object-Oriented Programming (OOPS)
* ✅ Functions
* ✅ Variables
* ✅ Loops
* ✅ Data Structures
* ✅ Algorithms

Each query is handled **independently (stateless)** to ensure fresh and concise responses, with no conversation memory.

---

## ✨ Features

* 🧑‍🎓 **Beginner-Friendly Explanations**
  Clear and simple answers designed for users new to programming.

* 💬 **Interactive Command-Line Interface**
  Ask questions via CLI and get instant AI-powered answers.

* 🧠 **Stateless Design**
  Each question is processed in isolation—no prior context is remembered.

* 🔒 **Secure Configuration**
  API keys and sensitive values are stored in a `.env` file.

* ⚡ **Lightweight Setup**
  No external tools or retrievers—just pure agent response.

---

## ⚙️ Prerequisites

Before running the app, ensure you have:

* 🐍 **Python 3.8+**
* 🌐 **Google API Key** for accessing Gemini via `google-genai`
* 🧠 **Google ADK** installed

---

## 📦 Dependencies

Install these Python packages:

```bash
pip install python-dotenv google-adk google-generativeai
```

**Used Packages:**

* `python-dotenv` – Load environment variables securely
* `google-adk` – Agent + session handling
* `google-generativeai` – Access Gemini model (`gemini-2.0-flash`)

---

## 🔐 Environment Configuration

Create a `.env` file in the root directory and add your API key:

```env
GOOGLE_API_KEY=your-api-key-here
```

> ⚠️ Never commit your API key to version control!

---

## 🖥️ Usage

### ▶️ Run the Application:

```bash
python main.py
```

### 💬 Interact with the Agent:

You'll see a prompt like:

```
You:
```

Ask a question, for example:

* `What is a function?`
* `What is OOPS in programming?`

To exit the conversation, type:

```bash
exit
```

---

## 📸 Screenshots

| Asking about functions                                                                                                              | Asking about OOPS                                                                                                               |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| <img width="700" alt="Function Screenshot" src="https://github.com/user-attachments/assets/f7e18d4e-0b36-44b1-a0ff-613a1782f1e0" /> | <img width="700" alt="OOPS Screenshot" src="https://github.com/user-attachments/assets/ccdd18e9-15c7-46bc-b510-3142bedf4c65" /> |

---

## 📚 Example Queries

Try asking:

* `Explain data structures with examples.`
* `What is the difference between a loop and recursion?`
* `How do algorithms work in real life?`

---

