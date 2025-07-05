# Product Requirements Document: Telegram AI Notebook Bot

*   **Version:** 1.0
*   **Date:** July 5, 2024
*   **Author:** Koluchiy
*   **Status:** In Development

## 1. Overview & Vision

### 1.1. Product Name
Telegram AI Notebook Bot (Internal codename: *Tele-Notebook*)

### 1.2. Vision
To create a Telegram-based personal AI assistant that empowers users to deeply understand and creatively interact with their documents and topics of interest. The bot will act like a personal "NotebookLM," allowing users to upload sources, ask questions, and generate insightful content like podcasts and mind maps directly within their favorite messenger.

### 1.3. Target Audience
*   Students and researchers who need to digest and summarize study materials.
*   Professionals who want to quickly extract key insights from reports, articles, and documents.
*   Content creators looking for an efficient way to script podcasts or visualize ideas.
*   Curious individuals who want to explore topics with an AI-powered research assistant.

## 2. Core Features (MVP - Minimum Viable Product)

### 2.1. Project & Source Management
*   **Requirement:** Users must be able to create and manage distinct "projects." Each project will be a separate container for documents and conversations.
*   **User Story:** As a user, I want to create a new project called "Q2 Marketing Report" so I can keep all related documents and queries separate from my "History Midterm" project.
*   **Implementation Details:**
    *   The bot will provide commands like `/newproject <name>`, `/switchproject <name>`, and `/listprojects`.
    *   The system will associate uploaded documents and conversation history with the user's currently active project.
    *   The backend will use the user's Telegram ID and the project name to partition data in the vector store.

### 2.2. Document Upload
*   **Requirement:** Users must be able to upload documents to their active project.
*   **User Story:** As a user, I want to upload a PDF file of a research paper to my project so the bot can use it as a source for answering my questions.
*   **Implementation Details:**
    *   The bot will support uploading of `.pdf`, `.txt`, and `.md` files initially.
    *   Upon upload, the backend will process the document (load, chunk, embed) and add it to the vector store associated with the user's active project.
    *   The bot will confirm successful processing to the user.

### 2.3. Source-Grounded Q&A
*   **Requirement:** Users must be able to ask questions and receive answers grounded in the documents they have uploaded to the current project.
*   **User Story:** As a user, after uploading my documents, I want to ask "What were the key findings of the study?" and get a summary based only on the information in those documents.
*   **Implementation Details:**
    *   This will be the default interaction mode. Any message that is not a command will be treated as a query.
    *   The backend will perform a RAG (Retrieval-Augmented Generation) lookup in the project's vector store to find relevant context.
    *   The retrieved context and the user's question will be passed to the LLM (Gemini) to generate a source-grounded answer.

### 2.4. Podcast Generation
*   **Requirement:** Users must be able to generate a short audio podcast based on their documents or a specified topic.
*   **User Story:** As a user, I want to issue a command like `/podcast on the main challenges` to receive an MP3 audio file summarizing that topic based on my project's sources.
*   **Implementation Details:**
    *   A `/podcast <topic>` command will trigger this feature.
    *   The bot will immediately acknowledge the command (e.g., "On it! Generating your podcast about 'main challenges'...") to provide instant feedback. The actual processing will happen in the background.
    *   The backend will use RAG to find sources relevant to the `<topic>`.
    *   The LLM (Gemini) will be prompted to generate a conversational podcast script from these sources.
    *   The generated script will be sent to the Piper TTS Docker service for audio synthesis.
    *   The final audio file (`.wav` or converted to `.mp3`) will be sent back to the user upon completion.

### 2.5. Mind Map Generation
*   **Requirement:** Users must be able to generate a visual mind map for a topic based on their sources.
*   **User Story:** As a user, I want to command `/mindmap on the proposed solutions` to get a PNG image that visually organizes the solutions discussed in my documents.
*   **Implementation Details:**
    *   A `/mindmap <topic>` command will trigger this feature.
    *   The bot will immediately acknowledge the command and notify the user that the mind map is being created.
    *   The backend will use RAG to find relevant sources.
    *   The LLM (Gemini) will be prompted to generate a structured representation of the topic in `Graphviz (DOT)` or `Mermaid.js` format.
    *   A server-side rendering tool (`graphviz` library) will convert this text representation into a PNG image.
    *   The bot will send the image back to the user upon completion.

### 2.6. Multi-Language Support
*   **Requirement:** The bot must support language selection for its responses and generated content (podcasts).
*   **User Story:** As a user, I want to set my language to German (`/lang de`) so that all Q&A responses, podcast scripts, and mind map text are generated in German.
*   **Implementation Details:**
    *   A `/lang <language_code>` command (`en`, `ru`, `de`) will set the user's preference.
    *   This language setting will be stored per user.
    *   All prompts sent to the LLM (Gemini) will include an instruction to "Respond in [selected language]."
    *   For podcasts, the system will select a corresponding Piper voice model for the chosen language. This requires pre-loading voice models for each supported language in the Piper service.

## 3. Non-Functional Requirements

### 3.1. Statefulness
The bot must remember the user's active project and language preference between interactions.

### 3.2. Error Handling
The bot must handle errors gracefully (e.g., failed API calls, invalid file types) and provide helpful feedback to the user.

### 3.3. Modularity & Maintainability
The architecture must be modular to allow for adding new features without requiring a full rewrite. Code should be clean, well-commented, and follow best practices.

## 4. Performance & Concurrency

### 4.1. Asynchronous Operation
*   **Requirement:** The bot must remain responsive to all users even while performing long-running tasks for one user (e.g., processing a large document, generating a podcast). A single user's request must not block the entire application.
*   **User Story:** As User A, I can chat with the bot and get instant answers to simple questions while User B is waiting for a 2-minute podcast to be generated.
*   **Implementation Details:**
    *   The core bot application will be built on an **asynchronous framework** (`asyncio` in Python).
    *   The `python-telegram-bot` library will be used in its `asyncio`-native mode.
    *   All I/O-bound operations (API calls to Gemini, requests to the Piper service, file operations) must be handled asynchronously using `await`.

### 4.2. Job Queuing for Intensive Tasks
*   **Requirement:** Computationally intensive tasks must be offloaded to a background process to prevent them from bogging down the main bot application.
*   **User Story:** As a user, when I upload a 100-page PDF, the bot acknowledges it instantly and processes it in the background, notifying me upon completion, without any noticeable slowdown in its chat responses.
*   **Implementation Details:**
    *   A **job queue system** (like **Celery** with **Redis** or **RabbitMQ** as a broker) will be implemented.
    *   Tasks like document ingestion/embedding, podcast script generation, and mind map creation will be defined as "background jobs."
    *   When a user triggers such a task, the main bot app will simply add a job to the queue and return an immediate acknowledgement to the user.
    *   One or more **worker processes** will run separately, picking up jobs from the queue and executing them.
    *   Upon job completion, the worker can use the Telegram Bot API to send the final result (podcast file, mind map image) back to the user who requested it.

## 5. Technical Stack & Architecture

*   **Platform:** Telegram
*   **Bot Framework:** `python-telegram-bot` (version 20+ for native `asyncio` support)
*   **Core Logic:** Python 3.11+ with `asyncio`
*   **Job Queue System:** **Celery**
*   **Message Broker:** **Redis** (or RabbitMQ) - for Celery to manage the job queue.
*   **LLM:** Google Gemini Pro API (via an asynchronous HTTP client like `aiohttp` or the official async-capable Google library).
*   **Text-to-Speech (TTS):** Piper TTS, deployed in a self-hosted Docker container.
*   **RAG Framework:** LangChain or LlamaIndex (using their asynchronous methods).
*   **Vector Database:** ChromaDB (or a more scalable option like Weaviate/Pinecone if user load increases).
*   **Mind Map Rendering:** Graphviz (via Python `graphviz` library).
*   **Architecture:**
    *   **Decoupled Three-Part System:**
        1.  **Main Bot App (Web Server):** A lightweight, asynchronous Python application. Its only jobs are to handle incoming Telegram updates, add tasks to the job queue, and provide quick, simple responses.
        2.  **Job Queue (Redis):** A message broker that acts as a buffer between the main app and the workers.
        3.  **Celery Workers:** One or more separate processes that consume tasks from the queue. These workers do all the heavy lifting: calling the Gemini API, processing documents, rendering mind maps, and interacting with the Piper service. This isolates long-running tasks from the user-facing bot.
    *   The Piper TTS service will remain a separate Docker container, called by the Celery workers.
    *   All secret keys will be managed via a `.env` file and not be committed to version control.

## 6. Future Enhancements (Post-MVP)

*   Support for more source types (e.g., web URLs, YouTube transcripts).
*   Interactive mind maps (e.g., using a web view).
*   User-selectable voices for podcasts.
*   Conversation history summary within a project.
*   Usage analytics for the bot owner.
*   Payment integration for premium features or higher usage limits.