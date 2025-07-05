# Lumenote: Your Personal AI Notebook on Telegram

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://telegram.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-Task%20Queue-green?style=for-the-badge&logo=celery)](https://docs.celeryq.dev/)
[![Gemini](https://img.shields.io/badge/Google-Gemini-orange?style=for-the-badge&logo=google-cloud)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-purple?style=for-the-badge)](https://www.langchain.com/)

Lumenote is a Telegram-based personal AI assistant that empowers you to deeply understand and creatively interact with your documents. It acts like a personal "NotebookLM," allowing you to upload sources, ask questions, and generate insightful content like podcasts and mind maps directly within your favorite messenger.

## Table of Contents

- [Features](#features)
- [Workflow Demo](#workflow-demo)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Setup and Installation](#setup-and-installation)
- [Project Structure](#project-structure)
- [Key Decisions & Troubleshooting](#key-decisions--troubleshooting)
- [Future Enhancements](#future-enhancements)

## Features

-   **Project Management**: Create distinct projects to keep your documents and conversations organized.
    -   `/newproject <name>`
    -   `/listprojects`
    -   `/switchproject <name>`
-   **Multi-Format Document Upload**: Upload your sources in `.pdf`, `.txt`, and `.md` formats. The bot processes and indexes them for retrieval.
-   **Source-Grounded Q&A**: Ask questions in plain text. Lumenote provides answers based *only* on the documents you've uploaded to the active project.
-   **AI Podcast Generation**: Generate a short, conversational audio podcast on any topic related to your documents.
    -   `/podcast <topic>`
-   **Visual Mind Map Creation**: Instantly visualize complex topics from your sources as a PNG mind map.
    -   `/mindmap <topic>`
-   **Multi-Language Support**: Interact with the bot and generate content in multiple languages.
    -   `/lang <en|ru|de>`

## Workflow Demo

1.  **Start a new project**:
    ```
    /newproject "History Midterm"
    ```
2.  **Upload your study materials**: Drag and drop your PDF lecture notes and `.txt` summaries into the chat.
3.  **Ask a question**:
    ```
    What were the main causes of the Peloponnesian War?
    ```
4.  **Get a summary podcast**:
    ```
    /podcast on the role of Sparta
    ```
5.  **Visualize the key players**:
    ```
    /mindmap of the Athenian League's leadership
    ```

## Architecture Overview

Lumenote is built on a robust, decoupled, and asynchronous architecture designed for responsiveness and scalability.



1.  **Telegram Bot App (`bot`)**: A lightweight, asynchronous Python application. Its only jobs are to handle incoming Telegram updates, provide instant feedback to the user, and add long-running tasks to the job queue.
2.  **Redis**: Acts as the message broker for Celery. It's the central nervous system that holds the queue of tasks to be processed.
3.  **Celery Workers (`worker`)**: One or more separate processes that do all the heavy lifting. They consume tasks from the Redis queue, process documents (embedding), call the Gemini LLM API, and generate podcasts/mind maps. This ensures the main bot app is never blocked.
4.  **Piper TTS (`piper`)**: A self-hosted Docker container providing a fast, high-quality Text-to-Speech engine. It's called by the Celery workers to synthesize audio for podcasts.
5.  **Shared Volumes**:
    -   `chroma_data`: Persists the ChromaDB vector database.
    -   `uploads_volume`: A shared space where the `bot` container places uploaded files and the `worker` container picks them up for processing.

## Tech Stack

| Category              | Technology                                   |
| --------------------- | -------------------------------------------- |
| **Bot Framework**     | `python-telegram-bot` (v21+)                 |
| **Core Logic**        | Python 3.11 with `asyncio`                   |
| **Job Queue System**  | Celery & Redis                               |
| **AI / LLM**          | Google Gemini Pro (via `langchain-google-genai`) |
| **RAG Framework**     | LangChain                                    |
| **Vector Database**   | ChromaDB                                     |
| **Text-to-Speech**    | Piper TTS (via `lscr.io/linuxserver/piper`)  |
| **Mind Map Rendering**| Graphviz                                     |
| **Orchestration**     | Docker & Docker Compose                      |

## Setup and Installation

### Step 1: Prerequisites

-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/)

### Step 2: Clone the Repository

```bash
git clone <your-repo-url>
cd LumeNote
```

### Step 3: Configure Environment

Create a `.env` file in the root directory by copying the example.

```bash
cp .env.example .env
```

Now, edit the `.env` file and add your secret keys:

```env
# --- Telegram ---
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# --- Google Gemini ---
GOOGLE_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"

# --- Service URLs (used within Docker network) ---
REDIS_URL="redis://redis:6379/0"
PIPER_TTS_URL="http://piper:5000/tts"

# --- ChromaDB Data Path ---
CHROMA_DB_PATH="./chroma_data"
```

**Important**: Do not commit your `.env` file to version control.

### Step 4: Build and Run

From the root directory, run the following command:

```bash
docker-compose up --build
```

-   This will build the custom Python image for the bot and worker, pull the official Redis and Piper images, and start all four containers.
-   **First-time setup**: The `piper` container will download the voice models for English, German, and Russian on its first startup. This may take a few minutes. You can monitor the progress in the logs.
-   To stop all services, press `Ctrl+C` in the terminal.

## Project Structure

<details>
<summary>Click to expand</summary>

```
LumeNote/
├── Dockerfile
├── docker-compose.yml
├── product_requirements.md
├── requirements.txt
└── tele_notebook/
    ├── __init__.py
    ├── bot/
    │   ├── handlers.py
    │   └── main.py
    ├── core/
    │   └── config.py
    ├── services/
    │   ├── llm_service.py
    │   ├── rag_service.py
    │   ├── tts_service.py
    │   └── user_service.py
    ├── tasks/
    │   ├── celery_app.py
    │   └── tasks.py
    └── utils/
        └── prompts.py
```

</details>

## Key Decisions & Troubleshooting

This project's development involved solving several common and complex issues related to modern distributed applications:

-   **Piper TTS Image**: The official `ghcr.io/rhasspy/piper` image proved unreliable due to authentication and manifest issues. We pivoted to the robust **`lscr.io/linuxserver/piper`** image, which required re-configuring the service to use environment variables instead of command-line arguments.
-   **Docker DNS Issues**: Early versions suffered from `Temporary failure in name resolution` errors inside the containers. This was solved by explicitly setting DNS servers (`8.8.8.8`) for each service in `docker-compose.yml`, a common fix for Docker networking on certain host systems.
-   **Library Versioning**: The project initially ran into a persistent telemetry bug in `chromadb`. The most reliable solution was to downgrade from a `0.5.x` release to the stable **`0.4.24`** version in `requirements.txt`.
-   **Shared File Handling**: We implemented a shared Docker volume (`uploads_volume`) to solve the "file not found" error when passing a file path from the `bot` container to the `worker` container, which have isolated filesystems.

## Future Enhancements

-   Support for more source types (e.g., web URLs, YouTube transcripts).
-   Interactive mind maps (e.g., using a web view).
-   User-selectable voices for podcasts.
-   Conversation history summary within a project.
-   Usage analytics for the bot owner.
-   Payment integration for premium features.