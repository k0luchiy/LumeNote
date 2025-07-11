# Product Requirements Document: Lumenote AI

*   **Version:** 2.0
*   **Date:** July 10, 2025
*   **Author:** Koluchiy
*   **Status:** Final

## 1. Overview & Vision

### 1.1. Product Name
Lumenote

### 1.2. Vision
To create an intelligent, autonomous research assistant on Telegram that empowers users to explore topics of interest. Lumenote transforms from a simple "notebook" into a proactive partner that discovers, ingests, and synthesizes information, allowing users to go from a topic idea to deep, source-grounded understanding and creative content generation with minimal effort.

### 1.3. Target Audience
*   **Students & Researchers:** Individuals needing to quickly gather and digest information on a new topic for a paper, presentation, or exam.
*   **Professionals & Analysts:** Users who need to get up to speed on a new industry, technology, or event by consuming and summarizing multiple sources.
*   **Content Creators:** Podcasters and writers looking for an efficient way to research a topic, gather source material, and generate initial scripts or idea maps.
*   **Lifelong Learners:** Curious individuals who want an AI-powered tool to explore new subjects in a structured and interactive way.

## 2. Core Features

### 2.1. Topic-Centric Project Management
*   **Requirement:** Users must be able to create projects centered around a specific topic of study rather than just a generic name. This topic becomes the core context for all subsequent actions within that project.
*   **User Story:** "As a student, I want to create a new project on 'the effects of neutron star mergers on element creation' so the bot knows the central theme of my research."
*   **Implementation Details:**
    *   The primary command for project creation is `/newproject <topic of study>`.
    *   The system will use the user's topic to generate a unique, system-friendly project ID for data storage (e.g., `user_123_neutron-star-merger`).
    *   The original, human-readable topic (e.g., "Neutron star merger") will be stored and associated with the project.
    *   Standard management commands like `/listprojects` and `/switchproject <name>` must remain functional.

### 2.2. Autonomous Source Discovery
*   **Requirement:** The bot must be able to autonomously search the web for relevant, high-quality sources based on the project's main topic.
*   **User Story:** "After creating my project, I want to type `/discover` and have the bot automatically find the top 5 most relevant articles or papers on my topic and add them to my project's knowledge base."
*   **Implementation Details:**
    *   A `/discover` command will trigger this feature.
    *   The bot will immediately acknowledge the request and inform the user that the process is running in the background.
    *   The backend will use a search API (e.g., Tavily) to find sources.
    *   The bot will report the list of discovered sources back to the user.
    *   Crucially, the bot will then automatically ingest the content of these sources into the project's vector database.
    *   A final, single "Success" message will be sent upon completion of the entire ingestion process. The user can then immediately begin asking questions.

### 2.3. Multi-Modal Source Ingestion
*   **Requirement:** Users must retain the ability to supplement the bot's discovered sources with their own local files or specific web links.
*   **User Story:** "The bot found some great general articles with `/discover`, but I also have a specific research paper as a PDF that I want to add to the project. I will simply upload the PDF file to the chat."
*   **User Story 2:** "I found a specific blog post I want to include. I will use the `/addsource <url>` command to add it directly."
*   **Implementation Details:**
    *   **File Upload:** The bot must support direct uploads of `.pdf`, `.txt`, and `.md` files.
    *   **URL Ingestion:** A `/addsource <url>` command must be available for users to add specific web pages. The backend will fetch, parse, and ingest the text content of the URL.
    *   All ingestion processes (discovery, file upload, URL add) will run as asynchronous background tasks to keep the bot responsive.

### 2.4. Context-Aware Content Generation
*   **Requirement:** The content generation commands (`/podcast`, `/mindmap`) must be intelligent. They should use the project's main topic as the default context if no specific topic is provided by the user.
*   **User Story:** "I've added all my sources. I want to just type `/podcast` and get an audio summary of my entire project's main topic without having to re-type it."
*   **User Story 2:** "For a more specific output, I want to type `/podcast on the role of kilonovas` and have the bot generate a podcast on that sub-topic, using the project's sources for context."
*   **Implementation Details:**
    *   `/podcast` (no arguments): The system will use the stored "main topic" of the active project to generate the script.
    *   `/podcast <specific topic>`: The system will use the user-provided `<specific topic>` for generation.
    *   The same logic applies to the `/mindmap` command.

### 2.5. Source-Grounded Q&A
*   **Requirement:** All user questions (plain text messages) must be answered strictly based on the information contained within the project's knowledge base (both discovered and user-uploaded sources).
*   **User Story:** "After the bot has processed all the sources on neutron star mergers, I want to ask 'What elements are created during a merger?' and get a factual answer based only on what's in the documents."
*   **Implementation Details:**
    *   The backend will use a RAG (Retrieval-Augmented Generation) pipeline.
    *   When a question is received, the system will perform a vector search against the active project's database to find the most relevant text chunks.
    *   These chunks (context) and the user's question will be passed to an LLM (Google Gemini) to generate the answer.

### 2.6. Multi-Language & User State Management
*   **Requirement:** The bot must be fully internationalized and remember user preferences across sessions.
*   **Implementation Details:**
    *   **Language:** A `/lang <en|de|ru>` command allows users to set their preferred language. All bot interface messages (help, status, confirmations) and all generated content (Q&A, podcast scripts, mind map text) must be in the selected language.
    *   **Statefulness:** The system must remember each user's `active_project` and `language` preference. This state must be safely shared between the main bot process and the background worker processes.

## 3. Non-Functional Requirements

### 3.1. Asynchronous & Non-Blocking Architecture
*   **Requirement:** The bot must remain responsive at all times. A long-running task for one user (like `/discover`) must not block or slow down the bot for any other user.
*   **Implementation:** The system is architected with a decoupled `bot` (receptionist) and `worker` (workhorse) model, orchestrated by a job queue (Celery & Redis). The `bot`'s only job is to validate input and enqueue tasks. All heavy processing (API calls, file I/O, database interactions) is handled exclusively by the `worker`.

### 3.2. Reliability & Error Handling
*   **Requirement:** Background tasks must be reliable. If a task fails, it should not be automatically retried in a way that creates a confusing user experience (e.g., duplicate messages).
*   **Implementation:** Critical, user-initiated tasks like `/discover` will be configured with `max_retries=0` to ensure they run exactly once, succeeding or failing cleanly. The bot must report clear success or error messages to the user.

### 3.3. Data Persistence & Integrity
*   **Requirement:** All user data, including project sources (vector embeddings) and user state, must persist across application restarts.
*   **Implementation:** The application will use named Docker volumes to persist the ChromaDB database files and user state files.

## 4. Technical Stack (Summary)

*   **Orchestration:** Docker & Docker Compose
*   **Bot Framework:** `python-telegram-bot`
*   **Job Queue:** Celery & Redis
*   **AI/LLM:** Google Gemini (for Q&A, scripting) & Gemini TTS (for audio)
*   **Web Search:** Tavily Search API
*   **Vector Database:** ChromaDB
*   **Core Logic:** Python 3.11 with `asyncio`