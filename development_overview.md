# Development Overview: Lumenote

This document provides a deep dive into the technical architecture, design decisions, and development workflow of the Lumenote project. It is intended for developers who will be working on or maintaining the codebase.

## Table of Contents

1.  [Core Philosophy & Vision](#1-core-philosophy--vision)
2.  [System Architecture](#2-system-architecture)
    -   [Diagram](#diagram)
    -   [Component Breakdown](#component-breakdown)
3.  [Technology Stack Rationale](#3-technology-stack-rationale)
4.  [Data Flow Deep Dive](#4-data-flow-deep-dive)
    -   [User Q&A (Async Task)](#user-qa-async-task)
    -   [Autonomous Source Discovery (Async Task)](#autonomous-source-discovery-async-task)
    -   [Manual Document Upload (Async Task)](#manual-document-upload-async-task)
5.  [Project Structure Explained](#5-project-structure-explained)
6.  [Key Configuration & Environment](#6-key-configuration--environment)
7.  [Development and Deployment Workflow](#7-development-and-deployment-workflow)
8.  [Troubleshooting and Debugging](#8-troubleshooting-and-debugging)

---

## 1. Core Philosophy & Vision

The primary goal of Lumenote is to provide a responsive, powerful, and autonomous AI research assistant on Telegram. The key architectural driver is **asynchronous, non-blocking operation, with a strict separation of concerns**. A user performing a simple, fast action should **never** be blocked by another user performing a long, slow action (like discovering and ingesting web sources).

This philosophy led to the decoupled, multi-component architecture centered around a Celery job queue, where the `bot` service acts as a pure "receptionist" and the `worker` service is the "workhorse".

## 2. System Architecture

Lumenote is not a monolithic application. It is a distributed system orchestrated by Docker Compose, composed of three primary services and two persistent data volumes. The original Piper TTS service has been deprecated in favor of the Google Gemini TTS API.

### Diagram

```mermaid
graph TD
    subgraph "User's Device"
        U(Telegram User)
    end

    subgraph "Docker Host"
        subgraph "Bot Service (bot)"
            B[Python: Telegram Bot App]
        end

        subgraph "Worker Service (worker)"
            W[Python: Celery Worker]
        end

        subgraph "Broker Service"
            R[Redis Broker]
        end

        subgraph "Persistent Storage"
            V_CHROMA[ChromaDB Volume]
            V_UPLOADS[Uploads Volume]
        end
    end
    
    subgraph "External APIs"
        G_API[Google Gemini API]
        T_API[Tavily Search API]
    end

    U -- /command, message, file --> B
    B -- Quick Reply (e.g. "On it!") --> U
    B -- Add Job (chat_id, user_id, topic, etc.) --> R

    W -- Pulls Job --> R
    W -- API Call --> T_API
    W -- API Call --> G_API
    
    W -- Read File --> V_UPLOADS
    W -- Store/Retrieve Embeddings --> V_CHROMA
    
    W -- Sends Final Result (text, audio, image) --> U
    
    B -- Saves Uploaded File --> V_UPLOADS
```

### Component Breakdown

-   **`bot` (The Receptionist)**:
    -   **Technology**: `python-telegram-bot` in `asyncio` mode.
    -   **Responsibility**: To be the fast, user-facing part of the system. It handles all incoming Telegram updates, validates user input, provides immediate acknowledgements ("Starting discovery..."), and its most important job is to **delegate all heavy work**. It places a "job" (a Python function call with arguments) onto the Redis queue. It performs **no** API calls to external services (Google, Tavily), no database interactions, and no file processing.

-   **`worker` (The Workhorse)**:
    -   **Technology**: `Celery` with a `Redis` backend, running in `-P solo` mode for `asyncio` compatibility.
    -   **Responsibility**: This is the engine of the application. It runs in the background, constantly watching the Redis queue for new jobs. When a job appears, it executes it. All business logic resides here:
        1.  Calling the **Tavily Search API** to discover sources.
        2.  Processing discovered web content or user-uploaded files.
        3.  Making expensive API calls to the **Google Gemini API** for embeddings, Q&A, and Text-to-Speech.
        4.  Interacting with the **ChromaDB** vector store on the `chroma_data` volume.
        5.  Rendering mind maps with the `graphviz` library.
        6.  Using its own `Bot` instance to send final results or status updates back to the user.

-   **`redis` (The Job Board)**:
    -   **Technology**: Official Redis Docker image.
    -   **Responsibility**: Acts as the intermediary message broker. It decouples the `bot` from the `worker`. If the worker is busy or crashes, the jobs remain safely in the Redis queue until a worker is available to process them. This makes the system resilient.

## 3. Technology Stack Rationale

| Technology | Reason for Choice |
| --- | --- |
| **Docker Compose** | Essential for managing a multi-service application. Defines the entire stack, networking, and volumes in a single, reproducible file. |
| **`python-telegram-bot`** | A mature, feature-rich library for Telegram bots with excellent `asyncio` support, critical for the non-blocking `bot` service. |
| **Celery & Redis** | The industry standard for background task processing in Python. It's robust, scalable, and perfectly suited for offloading long-running jobs. |
| **LangChain** | Provides high-level abstractions for building RAG pipelines, handling document loading, chunking, and chaining LLM calls. |
| **Google Gemini API** | The chosen Large Language Model for its powerful multi-modal capabilities (text, vision, TTS) at a competitive cost. |
| **Tavily Search API** | A simple and powerful search API designed for LLM applications, providing clean, relevant search results and content snippets. |
| **ChromaDB** | A simple, file-based vector database that is easy to set up for development and can be persisted with a simple Docker volume. |
| **Graphviz** | A powerful and standard tool for programmatically generating graphs, perfect for creating mind maps from structured LLM output. |
| **`pydantic-settings`** | Provides robust, type-safe loading of configuration from environment variables (`.env` file), preventing common configuration errors. |

## 4. Data Flow Deep Dive

### User Q&A (Async Task)

1.  User sends a text message (a question).
2.  The `bot` service's `handle_message` handler is triggered.
3.  The handler does a quick check to see if a project exists, sends a "Thinking..." acknowledgement, and immediately adds an `answer_question_task` to the Redis queue.
4.  The `worker` service picks up the job.
5.  The worker's task re-initializes a fresh ChromaDB client to get the latest data, creates a retriever, and passes the context and question to the Gemini API.
6.  The `worker` awaits the response and sends the final answer back to the user.

### Autonomous Source Discovery (Async Task)

1.  User sends the `/discover` command.
2.  The `bot` service's `discover` handler is triggered.
3.  It replies immediately: "Starting discovery..." and adds a `discover_sources_task` to the Redis queue. The `bot`'s work is done.
4.  The `worker` service picks up the `discover_sources_task`.
5.  The task calls the **Tavily API** to get a list of relevant sources and their content.
6.  The task sends a message to the user listing the found sources.
7.  The task then iterates through the sources, calling `rag_service.async_add_text_to_project` for each one to chunk, embed (via Gemini API), and store the vectors in ChromaDB.
8.  Upon completion of the entire loop, the `worker` sends a final "✅ Success!" message to the user.

### Manual Document Upload (Async Task)

1.  User uploads a PDF file.
2.  The `bot` service's `handle_document` handler is triggered.
3.  It immediately replies: "Got it! Processing your file..."
4.  It downloads the file and saves it to the shared `/app/uploads` volume.
5.  It adds a `process_document_task` to the Redis queue, passing the file path.
6.  The `worker` service picks up the job.
7.  It opens the file from the shared volume path, uses `rag_service` to chunk and embed it, and stores the vectors in ChromaDB.
8.  Upon completion, the `worker` notifies the user that the file has been added.

## 5. Project Structure Explained

-   **`bot/`**: Contains all code for the user-facing Telegram interface (`main.py`, `handlers.py`). This code is kept "thin" and is only responsible for receiving updates and dispatching tasks.
-   **`core/`**: Holds core application setup code, like `config.py` for loading environment variables.
-   **`locales/`**: Contains `.json` files for internationalization, allowing for easy translation of the bot's interface.
-   **`services/`**: A crucial directory containing business logic decoupled from the bot interface. Each file is a client for an external service (`llm_service` for Gemini, `rag_service` for ChromaDB) or core logic (`user_service` for state).
-   **`tasks/`**: Defines the background jobs run by Celery. `celery_app.py` is the configuration, and `tasks.py` contains the functions decorated with `@celery_app.task`, where all the heavy lifting occurs.
-   **`utils/`**: Helper functions and constants used across the application, like LLM `prompts.py` and `localization.py`.

## 6. Key Configuration & Environment

-   **`.env`**: Stores all secrets (Telegram, Google, Tavily). It is loaded by `pydantic-settings` in `core/config.py`. **Never commit this file.**
-   **`docker-compose.yml`**: The single source of truth for the application's infrastructure. It defines networking, service dependencies, and volume mounts.
-   **`requirements.txt`**: A pinned list of all Python dependencies.

## 7. Development and Deployment Workflow

1.  **Local Development**: `docker-compose up --build` is the primary command. It spins up the entire stack locally. Since the application code is mounted as a volume, changes to Python files are reflected instantly upon restarting the relevant containers (e.g., `docker-compose restart bot worker`).
2.  **Deployment**: The project is designed for any server with Docker and Docker Compose. The `docker-compose up -d` command runs the application in production.

## 8. Troubleshooting and Debugging

-   **View Logs**: The first step is always `docker-compose logs -f <service_name>`. The `worker` log is the most important for debugging business logic failures.
-   **Task Retries & Duplicate Messages**: If you see duplicate bot messages, it's a sign that a Celery task is failing and being retried. The solution was to explicitly set `max_retries=0` on the task decorator in `tasks.py` and wrap the task's logic in a `try...except` block to ensure it fails cleanly.
-   **"No Documents Found" After Ingestion**: This was a critical bug caused by a stale ChromaDB client. The `bot` and `worker` processes were not seeing a consistent view of the database. The fix was to move all database interactions exclusively to the `worker` process and to re-initialize the ChromaDB client within each task (`get_project_retriever`) to ensure it always reads the latest state from the disk volume.
-   **Telegram `httpx.ReadError`**: A common network timeout issue. Solved by increasing the `read_timeout` and `write_timeout` in the `python-telegram-bot` `ApplicationBuilder`.