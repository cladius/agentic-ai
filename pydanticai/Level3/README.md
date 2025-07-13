# 🔍 Level 3 – AI Assistant with Real-Time Web Search

## Overview

Implements a **tool-augmented AI agent** using the `pydantic-ai` framework. The agent answers user queries with real-time, web-sourced data using the `Tavily` search tool

## 🎯 Objective

Build an agent that:
- Integrates external tools (web search),
- Synthesizes relevant search results into coherent answers,
- Returns **only** the answer (not a raw list of links),
- Includes **credible sources** for user verification.

## 🧠 Technologies Used

- **Python** (async-based CLI app)
- **Pydantic AI** – Agent framework
- **Tavily Search API** – Real-time web search
- **OpenAI GPT-4o** – For language generation
- **Logfire** – For observability and debugging
- **dotenv** – For secure key management


## ⚙️ How It Works

-  User asks a question via CLI.
-  `Tavily` search tool is triggered for queries needing real-world data.
-  GPT-4o agent processes the search result and composes an answer.
-  Sources are listed at the bottom as a **numbered list of URLs**.
-  Logs and spans are sent to `Logfire` for each query-response pair.

## Example Interaction

AI Assistant (type 'quit' or 'exit' to end)
==================================================

Your question: Logfire project URL: https://logfire-eu.pydantic.dev/triptytiwari07/pydantic
latest on us tarrifs?
03:22:23.271 User session

Thinking...
03:22:23.272   Processing question
03:22:23.273     Tavily search

03:22:26.397       Tavily search completed
03:22:28.768     Response generated

==================================================
ANSWER:
As of June 11, 2025, President Trump's 50% tariffs on steel and aluminum remain in effect, upheld by an appeals court pending further legal challenges.  Trade negotiations between the U.S. and China are ongoing.


SOURCES:
1. https://www.reuters.com/business/tariffs/
2. https://finance.yahoo.com/news/live/trump-tariffs-live-updates-us-china-agree-on-plan-to-ease-trade-tensions-as-us-appeals-court-allows-tariffs-to-remain-in-effect-200619320.html
3. https://www.cbsnews.com/news/tariff-steel-aluminum-effective-date-trump/
4. https://www.cnn.com/2025/06/10/business/tariffs-appeals-court-stay-trump
5. https://www.pbs.org/newshour/world/china-and-u-s-will-hold-more-tariff-talks-trump-says-after-xi-call
==================================================
