# tasks/tasks.py

import os
import uuid
import graphviz
import asyncio
from telegram import Bot
from telegram.helpers import escape_markdown

from tele_notebook.core.config import settings
from tele_notebook.services import rag_service, llm_service, gemini_tts_service
from tele_notebook.tasks.celery_app import celery_app

# --- ASYNC HELPERS (The heavy lifting) ---

async def _async_discover_and_ingest(chat_id: int, user_id: int, project_name: str, main_topic: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        sources_list = await llm_service.discover_sources(main_topic)
        if not sources_list:
            await bot.send_message(chat_id=chat_id, text="I couldn't find any relevant sources."); return

        found_message = "Found these sources:\n\n"
        for i, item in enumerate(sources_list, 1):
            found_message += f"{i}\\. [{escape_markdown(item.get('title', 'Untitled'), version=2)}]({escape_markdown(item.get('url'), version=2)})\n"
        found_message += "\nNow processing them\\. This may take a moment\\.\\."
        await bot.send_message(chat_id=chat_id, text=found_message, parse_mode='MarkdownV2', disable_web_page_preview=True)

        tasks_completed = 0
        for source_item in sources_list:
            content = source_item.get('content')
            if content:
                metadata = {"source": source_item.get('url', 'Unknown'), "title": source_item.get('title', 'Untitled')}
                await rag_service.async_add_text_to_project(user_id, project_name, content, metadata)
                tasks_completed += 1
        
        if tasks_completed > 0:
            final_message = f"✅ Success\\! Added {tasks_completed} sources to project `{escape_markdown(project_name, version=2)}`\\. You can now ask questions\\."
            await bot.send_message(chat_id=chat_id, text=final_message, parse_mode='MarkdownV2')
        else:
            await bot.send_message(chat_id=chat_id, text="Found sources, but couldn't retrieve their content.")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ A critical error occurred during discovery: {e}")
        raise e # Re-raise to mark task as failed

async def _async_process_document(chat_id: int, user_id: int, project_name: str, file_path: str, file_type: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await rag_service.async_add_document_to_project(user_id, project_name, file_path, file_type)
        await bot.send_message(chat_id=chat_id, text=f"✅ Successfully added document to project '{project_name}'.")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ Error processing document: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

async def _async_handle_question(chat_id: int, user_id: int, project_name: str, question: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_chat_action(chat_id=chat_id, action='typing')
        # FIX: Re-initialize the retriever here to get the latest data
        retriever = rag_service.get_project_retriever(user_id, project_name)
        answer = await llm_service.get_rag_response(retriever, question, language)
        await bot.send_message(chat_id=chat_id, text=answer)
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ An error occurred: {e}")

async def _async_generate_podcast(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    file_name = f"/tmp/{uuid.uuid4()}.wav"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        script = await llm_service.generate_podcast_script(retriever, topic, language)
        audio_bytes = await gemini_tts_service.generate_podcast_audio(script, language)
        with open(file_name, "wb") as f: f.write(audio_bytes)
        with open(file_name, "rb") as audio_file:
            await bot.send_audio(chat_id=chat_id, audio=audio_file, title=f"Podcast on {topic}", filename=f"{topic}.wav")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ Couldn't generate podcast: {e}")
    finally:
        if os.path.exists(file_name): os.remove(file_name)

async def _async_generate_mindmap(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    file_path_base = f"/tmp/{uuid.uuid4()}"
    file_path_png = f"{file_path_base}.png"
    try:
        retriever = rag_service.get_project_retriever(user_id, project_name)
        dot_string = await llm_service.generate_mindmap_dot(retriever, topic, language)
        if not dot_string or not dot_string.strip().startswith("digraph"): raise ValueError("LLM did not return valid DOT.")
        graphviz.Source(dot_string).render(file_path_base, format='png', cleanup=True)
        with open(file_path_png, "rb") as image_file:
            await bot.send_photo(chat_id=chat_id, photo=image_file, caption=f"Mind Map for '{topic}'")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ Couldn't generate mind map: {e}")
    finally:
        if os.path.exists(file_path_png): os.remove(file_path_png)

# --- CELERY TASK DEFINITIONS ---

@celery_app.task(bind=True, max_retries=0, acks_late=True, ignore_result=True)
def discover_sources_task(self, chat_id: int, user_id: int, project_name: str, main_topic: str):
    try:
        asyncio.run(_async_discover_and_ingest(chat_id, user_id, project_name, main_topic))
    except Exception as exc:
        print(f"CRITICAL FAILURE in discover_sources_task: {exc}")
        raise exc # Re-raise to mark task as FAILED in Celery

@celery_app.task(acks_late=True)
def process_document_task(chat_id: int, user_id: int, project_name: str, file_path: str, file_type: str):
    asyncio.run(_async_process_document(chat_id, user_id, project_name, file_path, file_type))

@celery_app.task
def answer_question_task(chat_id: int, user_id: int, project_name: str, question: str, language: str):
    asyncio.run(_async_handle_question(chat_id, user_id, project_name, question, language))

@celery_app.task
def generate_podcast_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    asyncio.run(_async_generate_podcast(chat_id, user_id, project_name, topic, language))

@celery_app.task
def generate_mindmap_task(chat_id: int, user_id: int, project_name: str, topic: str, language: str):
    asyncio.run(_async_generate_mindmap(chat_id, user_id, project_name, topic, language))