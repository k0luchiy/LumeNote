# Lumenote: Your Autonomous AI Research Assistant on Telegram

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://telegram.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-Task%20Queue-green?style=for-the-badge&logo=celery)](https://docs.celeryq.dev/)
[![Gemini](https://img.shields.io/badge/Google-Gemini%20Pro-orange?style=for-the-badge&logo=google-cloud)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-purple?style=for-the-badge)](https://www.langchain.com/)

Lumenote is an intelligent, autonomous research assistant on Telegram that transforms how you learn about new topics. Go from a single idea to a deep, source-grounded understanding by letting Lumenote discover relevant web sources, process your own documents, and generate insightful content like podcasts and mind maps.

## Table of Contents

- [Features](#features)
- [Workflow Demo](#workflow-demo)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Setup and Installation](#setup-and-installation)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Key Decisions & Troubleshooting](#key-decisions--troubleshooting)

## Features

-   **Topic-Centric Projects**: Create projects based on a topic of study, like "The History of Ancient Rome" or "Quantum Computing Applications".
-   **Autonomous Source Discovery**: Use the `/discover` command to have the bot automatically search the web, find the most relevant articles, and add them to your project's knowledge base.
-   **Multi-Modal Document Upload**: Supplement discovered sources by uploading your own documents (`.pdf`, `.txt`, `.md`) or adding specific web pages with the `/addsource` command.
-   **Source-Grounded Q&A**: Ask questions in plain text. Lumenote provides answers based *only* on the documents within your active project.
-   **Context-Aware AI Podcast Generation**: Generate a short, conversational audio podcast. Use `/podcast` to get a summary of your project's main topic, or `/podcast <sub-topic>` for a more focused segment.
-   **Visual Mind Map Creation**: Instantly visualize complex topics from your sources as a PNG mind map with `/mindmap` or `/mindmap <sub-topic>`.
-   **Multi-Language Support**: Interact with the bot and generate content in multiple languages (English, German, Russian supported).

## Workflow Demo

1.  **Start a new research project**:
    ```
    /newproject The merger of neutron stars
    ```
2.  **Let the bot find sources for you**:
    ```
    /discover
    ```
    *(Lumenote will search the web and automatically process the top 5 sources.)*

3.  **Upload your own lecture notes**:
    *Drag and drop your ` astrophysics-notes.pdf` into the chat.*

4.  **Ask a specific question**:
    ```
    What elements are created during a kilonova event?
    ```
5.  **Get a podcast summary of the entire topic**:
    ```
    /podcast
    ```
6.  **Visualize a sub-topic**:
    ```
    /mindmap gravitational waves from mergers
    ```

## Architecture Overview

Lumenote is built on a robust, decoupled, and asynchronous architecture designed for responsiveness and scalability. A user's long-running task (like `/discover`) will never block the bot for other users.

1.  **Telegram Bot (`bot`)**: A lightweight, asynchronous Python application. Its only job is to handle incoming Telegram updates, provide instant feedback to the user (e.g., "On it!"), and add long-running tasks to the job queue.
2.  **Redis**: The message broker for Celery. It's the central "job board" that holds the queue of tasks to be processed, decoupling the `bot` from the `worker`.
3.  **Celery Worker (`worker`)**: A separate process that does all the heavy lifting. It consumes tasks from the Redis queue, such as:
    -   Calling the Tavily API to discover sources.
    -   Processing and embedding user-uploaded files and discovered web content.
    -   Calling the Google Gemini API for Q&A, scriptwriting, and TTS.
    -   Rendering mind maps with Graphviz.
4.  **Shared Volumes**: Docker volumes are used to persist data across container restarts, including the ChromaDB vector database (`chroma_data`) and temporarily uploaded files (`uploads_volume`).

## Tech Stack

| Category | Technology |
| --- | --- |
| **Bot Framework** | `python-telegram-bot` (v21+) |
| **Core Logic** | Python 3.11 with `asyncio` |
| **Job Queue System** | Celery & Redis |
| **AI / LLM** | Google Gemini Pro |
| **Text-to-Speech** | Google Gemini TTS |
| **Web Search** | Tavily Search API |
| **RAG Framework** | LangChain |
| **Vector Database** | ChromaDB |
| **Mind Map Rendering**| Graphviz |
| **Orchestration** | Docker & Docker Compose |

## Setup and Installation

### Step 1: Prerequisites

-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### Step 2: Clone the Repository

```bash
git clone <your-repo-url>
cd lumenote
```

### Step 3: Configure Environment

Create a `.env` file in the root directory by copying the example.

```bash
cp .env.example .env
```

Now, edit the `.env` file and add your secret keys. You will need keys from Telegram, Google AI, and Tavily.

```env
# --- Telegram ---
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# --- Google Gemini ---
GOOGLE_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"

# --- Tavily Search API ---
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"

# --- Service URLs (used within Docker network) ---
REDIS_URL="redis://redis:6379/0"

# --- ChromaDB Data Path ---
CHROMA_DB_PATH="./chroma_data"
```

**Important**: Do not commit your `.env` file to version control.

### Step 4: Build and Run

From the root directory, run the following command:

```bash
docker-compose up --build
```

-   This will build the custom Python image for the `bot` and `worker`, pull the official Redis image, and start all containers.
-   The first startup might take a moment as images are downloaded.
-   To run in the background (detached mode), use `docker-compose up --build -d`.
-   To view logs: `docker-compose logs -f <service_name>` (e.g., `worker`).
-   To stop all services, press `Ctrl+C` in the terminal (or `docker-compose down` if detached).

## Usage Guide

| Command | Description |
| --- | --- |
| `/newproject <topic>` | Creates a new project based on your topic of study. |
| `/discover` | Automatically finds and adds relevant web sources to your project. |
| `/addsource <url>` | Manually adds a specific web page as a source. |
| `/listprojects` | Shows all your projects. |
| `/switchproject <name>` | Switches your active project. |
| `/podcast [topic]` | Generates a podcast. Uses the main project topic if none is provided. |
| `/mindmap [topic]` | Generates a mind map. Uses the main project topic if none is provided. |
| `/lang <en\|ru\|de>` | Sets the bot's language. |
| `/status` | Shows your current active project, topic, and language. |
| `/help` | Displays the list of available commands. |

## Project Structure

```
lumenote/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── tele_notebook/
    ├── __init__.py
    ├── bot/
    │   ├── handlers.py
    │   └── main.py
    ├── core/
    │   └── config.py
    ├── locales/
    │   ├── de.json
    │   ├── en.json
    │   └── ru.json
    ├── services/
    │   ├── gemini_tts_service.py
    │   ├── llm_service.py
    │   └── rag_service.py
    │   └── user_service.py
    ├── tasks/
    │   ├── celery_app.py
    │   └── tasks.py
    └── utils/
        ├── audio_utils.py
        ├── localization.py
        └── prompts.py
```

## Key Decisions & Troubleshooting

This project's architecture evolved to solve common issues in distributed, AI-powered applications:

-   **Asynchronous Offloading**: All heavy operations are delegated to a Celery worker to ensure the bot's UI remains responsive. The `bot` service is a pure "receptionist".
-   **Task Reliability**: The critical `/discover` task is configured with `max_retries=0` in Celery to prevent it from running multiple times on failure, which would cause duplicate messages and a confusing user experience.
-   **Database Consistency**: To solve issues where the `answer_question_task` couldn't see data added by `discover_sources_task`, the ChromaDB client is now re-initialized within each task that needs it. This ensures the worker always reads the latest state from the shared disk volume, rather than relying on a potentially stale, cached client object.
-   **Network Stability**: Timeouts between the bot and Telegram's servers (`httpx.ReadError`) were resolved by setting explicit `read_timeout` and `write_timeout` values in the `ApplicationBuilder`.
-   **Markdown Escaping**: Telegram's strict `MarkdownV2` parser requires careful escaping of special characters. All user-facing messages are now programmatically escaped to prevent parsing errors.