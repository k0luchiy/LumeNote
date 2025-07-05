import os
import uuid
import graphviz
import asyncio
from telegram import Bot
from tele_notebook.core.config import settings
from tele_notebook.services import rag_service, llm_service, tts_service
from tele_notebook.tasks.celery_app import celery_app

# Instantiate a Bot object to send messages from the worker
# It's okay to create this here as it's a lightweight object.
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_telegram_message(chat_id: int, text: str):
    """Async helper to send a message."""
    await bot.send_message(chat_id=chat_id, text=text)

async def send_telegram_audio(chat_id: int, audio_path: str, title: str, filename: str):
    """Async helper to send an audio file."""
    with open(audio_path, "rb") as audio_file:
        await bot.send_audio(chat_id=chat_id, audio=audio_file, title=title, filename=filename)

async def send_telegram_photo(chat_id: int, photo_path: str, caption: str):
    """Async helper to send a photo."""
    with open(photo_path, "rb") as image_file:
        await bot.send_photo(chat_id=chat_id, photo=image_file, caption=caption)


@celery_app.task
def process_document_task(chat_id: int, user_id: int, project_name: str, file_path: str, file_type: str):
    try:
        rag_service.add_document_to_project(user_id, project_name, file_path, file_type)
        message = f"✅ Successfully added document to project '{project_name}'."
        asyncio.run(send_telegram_message(chat_id, message))
    except Exception as e:
        error_message = f"❌ Error processing document: {e}"
        asyncio.run(send_telegram_message(chat_id, error_message))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@celery_app.task
def generate_podcast_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    file_name = f"/tmp/{uuid.uuid4()}.wav"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        
        script = asyncio.run(llm_service.generate_podcast_script(retriever, topic, language))
        audio_bytes = asyncio.run(tts_service.synthesize_audio(script, language))

        with open(file_name, "wb") as f:
            f.write(audio_bytes)

        asyncio.run(send_telegram_audio(chat_id, file_name, f"Podcast on {topic}", f"{topic}.wav"))

    except Exception as e:
        error_message = f"❌ Sorry, I couldn't generate the podcast: {e}"
        asyncio.run(send_telegram_message(chat_id, error_message))
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

@celery_app.task
def generate_mindmap_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    file_path_base = f"/tmp/{uuid.uuid4()}"
    file_path_png = f"{file_path_base}.png"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        
        dot_string = asyncio.run(llm_service.generate_mindmap_dot(retriever, topic, language))

        if not dot_string or not dot_string.strip().startswith("digraph"):
            raise ValueError("LLM did not return a valid DOT language graph.")

        graphviz.Source(dot_string).render(file_path_base, format='png', cleanup=True)
        
        asyncio.run(send_telegram_photo(chat_id, file_path_png, f"Mind Map for '{topic}'"))
            
    except Exception as e:
        error_message = f"❌ Sorry, I couldn't generate the mind map: {e}"
        asyncio.run(send_telegram_message(chat_id, error_message))
    finally:
        if os.path.exists(file_path_png):
            os.remove(file_path_png)