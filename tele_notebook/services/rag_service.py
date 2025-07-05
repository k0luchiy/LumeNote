# FILE: tele_notebook/services/rag_service.py

import chromadb
# REMOVED ChromaSettings as it's not needed for disabling telemetry in this version
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from tele_notebook.core.config import settings
import os

# FIX: Disable ChromaDB's telemetry using the older method for version 0.4.x
from chromadb.config import Settings as ChromaSettings
client = chromadb.PersistentClient(
    path=settings.CHROMA_DB_PATH,
    settings=ChromaSettings(anonymized_telemetry=False)
)


# REMOVED the google_api_key argument. The library will find it in the environment.
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def get_collection_name(user_id: int, project_name: str) -> str:
    return f"user_{user_id}_{project_name.lower().replace(' ', '_')}"

def add_document_to_project(user_id: int, project_name: str, file_path: str, file_type: str):
    """Processes and adds a document to the user's project vector store."""
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

    # FIX: The API for 0.4.24 uses persist_directory and does not take a client argument here.
    # The client is used under the hood when a persist_directory is provided.
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=settings.CHROMA_DB_PATH
    )
    vectorstore.persist()
    print(f"Added {len(splits)} chunks to collection '{collection_name}'")

def get_project_retriever(user_id: int, project_name: str):
    """Gets a retriever for a specific project."""
    collection_name = get_collection_name(user_id, project_name)
    # FIX: The API for 0.4.24 uses persist_directory.
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DB_PATH
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})