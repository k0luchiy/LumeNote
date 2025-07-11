# services/llm_service.py

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults # <-- ADD IMPORT
from tele_notebook.utils import prompts
from langchain_core.documents import Document  # <-- ADD THIS IMPORT

import asyncio # <--- ADD THIS IMPORT
from tavily import TavilyClient # <--- ADD THIS IMPORT
from tele_notebook.core.config import settings # <--- ADD THIS IMPORT

# REMOVE the global llm object
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

async def get_rag_response(retriever, question: str, language: str) -> str:
    # CREATE the llm object here, inside the async function
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro") # Note: I've updated to 1.5-pro as it's generally better.
    prompt = prompts.get_qa_prompt(language)

    rag_chain = (
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return await rag_chain.ainvoke(question)

async def generate_podcast_script(retriever, topic: str, language:str) -> str:
    # CREATE the llm object here, inside the async function
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
    prompt = prompts.get_podcast_prompt(language)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "topic": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return await chain.ainvoke(topic)

async def generate_mindmap_dot(retriever, topic: str, language: str) -> str:
    # CREATE the llm object here, inside the async function
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
    prompt = prompts.get_mindmap_prompt(language)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "topic": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    response = await chain.ainvoke(topic)
    # Clean up the response to extract only the DOT code
    if "```dot" in response:
        return response.split("```dot")[1].split("```")[0].strip()
    return response


def _blocking_tavily_search(topic: str) -> dict:
    """Performs a synchronous search using the TavilyClient."""
    tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    
    # --- THIS IS THE KEY CHANGE ---
    # We now explicitly ask for the content of each page.
    # We also specify the number of results we want.
    response = tavily_client.search(
        query=topic, 
        search_depth="basic",
        include_answer=False,
        max_results=5 # Let's get 5 sources
    )
    return response

async def discover_sources(topic: str) -> list[dict]:
    """
    Uses Tavily to search for sources and their content on a given topic.
    """
    response_dict = await asyncio.to_thread(_blocking_tavily_search, topic)
    # Return the list of results from the JSON response
    return response_dict.get("results", [])