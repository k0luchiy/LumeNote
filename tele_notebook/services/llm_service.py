from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from tele_notebook.utils import prompts

# REMOVED the google_api_key argument. The library will find it in the environment.
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

async def get_rag_response(retriever, question: str, language: str) -> str:
    prompt = prompts.get_qa_prompt(language)

    rag_chain = (
        {"context": retriever, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return await rag_chain.ainvoke(question)

async def generate_podcast_script(retriever, topic: str, language: str) -> str:
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