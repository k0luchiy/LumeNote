# services/rag_service.py

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from tele_notebook.core.config import settings
import os

# Disable ChromaDB's telemetry
client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_PATH,
    settings=ChromaSettings(anonymized_telemetry=False)
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def get_collection_name(user_id: int, project_name: str) -> str:
    return f"user_{user_id}_{project_name.lower().replace(' ', '_')}"

# NEW: Create an async version of the document processing function
async def async_add_document_to_project(user_id: int, project_name: str, file_path: str, file_type: str):
    """Processes and adds a document to the user's project vector store asynchronously."""
    collection_name = get_collection_name(user_id, project_name)

    if file_type == 'pdf':
        loader = PyPDFLoader(file_path)
    elif file_type in ['txt', 'md']:
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    # Use the async version of the Chroma function
    await Chroma.afrom_documents(
        client=client,
        documents=splits,
        embedding=embeddings,
        collection_name=collection_name
    )
    print(f"Added {len(splits)} chunks to collection '{collection_name}'")


def get_project_retriever(user_id: int, project_name: str):
    """Gets a retriever for a specific project. This is still synchronous and fine."""
    collection_name = get_collection_name(user_id, project_name)
    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})