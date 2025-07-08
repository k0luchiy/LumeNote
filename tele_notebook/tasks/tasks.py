# tasks/tasks.py

import os
import uuid
import graphviz
import asyncio
from telegram import Bot  # Keep the import
from tele_notebook.core.config import settings
from tele_notebook.services import rag_service, llm_service, tts_service
from tele_notebook.tasks.celery_app import celery_app

# REMOVE THE GLOBAL BOT OBJECT FROM HERE
# bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

# --- ASYNC HELPER FUNCTIONS ---

async def _async_process_document(chat_id: int, user_id: int, project_name: str, file_path: str, file_type: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)  # CREATE BOT OBJECT HERE
    try:
        await rag_service.async_add_document_to_project(user_id, project_name, file_path, file_type)
        message = f"✅ Successfully added document to project '{project_name}'."
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        error_message = f"❌ Error processing document: {e}"
        await bot.send_message(chat_id=chat_id, text=error_message)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def _async_generate_podcast(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)  # CREATE BOT OBJECT HERE
    file_name = f"/tmp/{uuid.uuid4()}.wav"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        script = await llm_service.generate_podcast_script(retriever, topic, language)
        audio_bytes = await tts_service.synthesize_audio(script, language)
        with open(file_name, "wb") as f:
            f.write(audio_bytes)
        with open(file_name, "rb") as audio_file:
            await bot.send_audio(chat_id=chat_id, audio=audio_file, title=f"Podcast on {topic}", filename=f"{topic}.wav")
    except Exception as e:
        error_message = f"❌ Sorry, I couldn't generate the podcast: {e}"
        await bot.send_message(chat_id=chat_id, text=error_message)
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

async def _async_generate_mindmap(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)  # CREATE BOT OBJECT HERE
    file_path_base = f"/tmp/{uuid.uuid4()}"
    file_path_png = f"{file_path_base}.png"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        dot_string = await llm_service.generate_mindmap_dot(retriever, topic, language)
        if not dot_string or not dot_string.strip().startswith("digraph"):
            raise ValueError("LLM did not return a valid DOT language graph.")
        graphviz.Source(dot_string).render(file_path_base, format='png', cleanup=True)
        with open(file_path_png, "rb") as image_file:
            await bot.send_photo(chat_id=chat_id, photo=image_file, caption=f"Mind Map for '{topic}'")
    except Exception as e:
        error_message = f"❌ Sorry, I couldn't generate the mind map: {e}"
        await bot.send_message(chat_id=chat_id, text=error_message)
    finally:
        if os.path.exists(file_path_png):
            os.remove(file_path_png)

async def _async_handle_question(chat_id: int, user_id: int, project_name: str, question: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)  # CREATE BOT OBJECT HERE
    try:
        await bot.send_chat_action(chat_id=chat_id, action='typing')
        retriever = rag_service.get_project_retriever(user_id, project_name)
        answer = await llm_service.get_rag_response(retriever, question, language)
        await bot.send_message(chat_id=chat_id, text=answer)
    except Exception as e:
        error_message = f"❌ Sorry, an error occurred while fetching the answer: {e}"
        await bot.send_message(chat_id=chat_id, text=error_message)

# --- CELERY TASK DEFINITIONS (No changes here) ---

@celery_app.task
def process_document_task(chat_id: int, user_id: int, project_name: str, file_path: str, file_type: str):
    asyncio.run(_async_process_document(chat_id, user_id, project_name, file_path, file_type))

@celery_app.task
def generate_podcast_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    asyncio.run(_async_generate_podcast(chat_id, user_id, project_name, topic, language))

@celery_app.task
def generate_mindmap_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    asyncio.run(_async_generate_mindmap(chat_id, user_id, project_name, topic, language))

@celery_app.task
def answer_question_task(chat_id: int, user_id: int, project_name: str, question: str, language: str):
    asyncio.run(_async_handle_question(chat_id, user_id, project_name, question, language))