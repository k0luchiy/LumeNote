from langchain_core.prompts import ChatPromptTemplate

# Supported languages and their corresponding Piper voice models
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "voice": "en_US-lessac-medium"},
    "ru": {"name": "Russian", "voice": "ru_RU-irina-medium"},
    "de": {"name": "German", "voice": "de_DE-thorsten-medium"},
}

def get_qa_prompt(language: str) -> ChatPromptTemplate:
    lang_name = SUPPORTED_LANGUAGES.get(language, {"name": "English"})["name"]
    return ChatPromptTemplate.from_messages([
        ("system", f"You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise. Respond in {lang_name}."),
        ("user", "Question: {input}\n\nContext:\n{context}"),
    ])

def get_podcast_prompt(language: str) -> ChatPromptTemplate:
    lang_name = SUPPORTED_LANGUAGES.get(language, {"name": "English"})["name"]
    return ChatPromptTemplate.from_template(
        f"""You are a podcast script writer. Based on the provided context, write a short, engaging, and conversational podcast script about the topic: '{{topic}}'.
The script should be natural-sounding. Start with a brief introduction and end with a concluding thought.
The entire script should be around 150-200 words.
Your entire output must be only the script content, without any titles, headers, or "Host 1:" markers.
The script MUST be in {lang_name}.

Context:
{{context}}

Topic: {{topic}}

Podcast Script:"""
    )

# utils/prompts.py (The new, corrected version)

def get_mindmap_prompt(language: str) -> ChatPromptTemplate:
    lang_name = SUPPORTED_LANGUAGES.get(language, {"name": "English"})["name"]
    return ChatPromptTemplate.from_template(
        f"""You are an AI assistant that generates mind maps in the Graphviz DOT language.
Based on the provided context, create a mind map for the topic: '{{topic}}'.
The mind map should have a central topic and several branching nodes with key ideas. Keep the text in nodes concise.
The text within the mind map nodes MUST be in {lang_name}.
Your entire output must be ONLY the DOT language code, enclosed in a single ```dot ... ``` block. Do not include any other text or explanation.

Example format:
```dot
digraph G {{{{  # CORRECT: Use 4 open braces to escape for both f-string and LangChain
    rankdir=LR;
    node [shape=box, style="rounded,filled", fillcolor=lightblue];
    "Central Topic" -> "Idea 1";
    "Central Topic" -> "Idea 2";
    "Idea 1" -> "Detail A";
}}}}```  # CORRECT: Use 4 close braces
Context:
{{context}}

Topic: {{topic}}

DOT Language Output:"""
    )