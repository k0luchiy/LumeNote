# handlers.py

import logging
import os
import uuid
import requests
from bs4 import BeautifulSoup
import re 

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from tele_notebook.services import user_service, rag_service
from tele_notebook.tasks import tasks
from tele_notebook.utils.prompts import SUPPORTED_LANGUAGES
from tele_notebook.utils.localization import get_text

logger = logging.getLogger(__name__)

def _get_lang(user_id: int) -> str:
    return user_service.get_user_state(user_id).get("language", "en")

# --- CORE COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang_code = _get_lang(user.id)
    text = get_text("welcome", lang_code, user_mention=user.mention_markdown_v2())
    await update.message.reply_markdown_v2(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _get_lang(update.effective_user.id)
    text = get_text("help", lang_code)
    await update.message.reply_markdown_v2(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    response_lang_code = _get_lang(user_id) 
    state = user_service.get_user_state(user_id)
    project = state.get('active_project', 'default')
    main_topic = state.get('main_topic', 'Not set')
    user_lang_setting = state.get('language', 'en') 
    lang_name = SUPPORTED_LANGUAGES.get(user_lang_setting, {}).get('name', 'English')
    text = get_text(
        "status",
        lang_code=response_lang_code,
        user_id=f"`{user_id}`", 
        project=f"`{escape_markdown(project, version=2)}`", 
        main_topic=f"*{escape_markdown(main_topic, version=2)}*",
        lang_name=f"`{escape_markdown(lang_name, version=2)}`",
        display_lang_code=f"`{escape_markdown(user_lang_setting, version=2)}`" 
    )
    await update.message.reply_markdown_v2(text)

# --- PROJECT MANAGEMENT ---
async def new_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    main_topic = " ".join(context.args)
    if not main_topic:
        text = get_text("provide_project_topic", lang_code)
        await update.message.reply_markdown_v2(text); return
    project_name = rag_service.get_collection_name(user_id, main_topic)
    user_service.set_user_state(user_id, project=project_name, main_topic=main_topic)
    text = get_text("project_topic_created", lang_code, project_name=project_name, main_topic=main_topic)
    await update.message.reply_text(text)

async def list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    projects = user_service.get_user_display_projects(user_id) 
    if not projects:
        text = get_text("no_projects", lang_code); await update.message.reply_markdown_v2(text); return

    project_list = "\n".join(f"\\- `{escape_markdown(p, version=2)}`" for p in projects)
    text = get_text("your_projects", lang_code, project_list=project_list)
    await update.message.reply_markdown_v2(text)

async def switch_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    project_name = " ".join(context.args)
    if not project_name:
        text = get_text("switch_provide_name", lang_code); await update.message.reply_markdown_v2(text); return
    if project_name not in user_service.get_user_projects(user_id):
        text = get_text("project_not_found", lang_code, project_name=project_name); await update.message.reply_text(text); return
    user_service.set_user_state(user_id, project=project_name)
    text = get_text("switched_project", lang_code, project_name=project_name)
    await update.message.reply_text(text)

# --- LANGUAGE ---
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supported_codes = ", ".join(f"`{key}`" for key in SUPPORTED_LANGUAGES.keys())
    if not context.args or context.args[0] not in SUPPORTED_LANGUAGES:
        text = get_text("lang_usage", lang_code=_get_lang(user_id), supported_codes=supported_codes); await update.message.reply_markdown_v2(text); return
    new_lang_code = context.args[0]
    user_service.set_user_state(user_id, lang=new_lang_code)
    lang_name = SUPPORTED_LANGUAGES[new_lang_code]['name']
    text = get_text("lang_set", new_lang_code, lang_name=lang_name)
    await update.message.reply_text(text)

# --- FEATURE HANDLERS ---
async def discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    main_topic = state.get("main_topic")
    if not main_topic or not project_name or project_name == "default":
        await update.message.reply_text(get_text("create_project_first", lang_code)); return
    await update.message.reply_text(f"🔍 Starting discovery for '{main_topic}'. I'll report back as I find and process sources.")
    tasks.discover_sources_task.delay(update.effective_chat.id, user_id, project_name, main_topic)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    if not project_name or project_name == "default":
        await update.message.reply_text(get_text("create_project_first", lang_code)); return
    doc = update.message.document
    file_ext = doc.file_name.split('.')[-1].lower()
    if file_ext not in ['pdf', 'txt', 'md']:
        await update.message.reply_text(get_text("unsupported_file_type", lang_code, supported_types='pdf, txt, md')); return
    await update.message.reply_text(get_text("processing_file", lang_code, file_name=doc.file_name))
    shared_uploads_dir = "/app/uploads"
    os.makedirs(shared_uploads_dir, exist_ok=True)
    temp_file_path = f"{shared_uploads_dir}/{uuid.uuid4()}_{doc.file_name}"
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(temp_file_path)
    tasks.process_document_task.delay(update.effective_chat.id, user_id, project_name, temp_file_path, file_ext)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    question = update.message.text
    chat_id = update.effective_chat.id

    if not project_name or project_name == "default":
        await update.message.reply_text(get_text("create_project_first", lang_code))
        return

    # --- DISABLING THE CHECK AS REQUESTED ---
    # This allows the task to proceed so we can see the real error in the worker logs.
    # if project_name not in user_service.get_user_projects(user_id):
    #     await update.message.reply_text(get_text("no_documents_in_project", lang_code))
    #     return

    await update.message.reply_text(get_text("thinking", lang_code))
    tasks.answer_question_task.delay(chat_id, user_id, project_name, question, lang_code)

async def generate_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, task_function, command_name: str):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    if not project_name or project_name == "default":
        await update.message.reply_text(get_text("select_project_first", lang_code)); return
    if not context.args:
        topic = state.get("main_topic")
        if not topic:
            await update.message.reply_text("No topic given and project has no main topic."); return
    else:
        topic = " ".join(context.args)
    content_type = "podcast" if command_name == "podcast" else "mind map"
    await update.message.reply_text(get_text("generating_content", lang_code, content_type=content_type, topic=topic))
    task_function.delay(update.effective_chat.id, user_id, project_name, topic, lang_code)

# In handlers.py, add this entire function
async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    
    if not project_name or project_name == "default":
        await update.message.reply_text(get_text("create_project_first", lang_code))
        return

    if not context.args:
        # You should add a key like "provide_url" to your localization files
        await update.message.reply_text("Please provide a URL. Usage: /addsource <url>")
        return
    
    url = context.args[0]
    await update.message.reply_text(f"Fetching content from {url}...")

    try:
        # Fetch and parse web page content
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # A simple way to get cleaner text
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        page_text = soup.get_text(separator='\n', strip=True)

        # Save content to a temporary .txt file
        shared_uploads_dir = "/app/uploads"
        os.makedirs(shared_uploads_dir, exist_ok=True)
        # Use the URL to create a somewhat readable filename
        safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', url)
        temp_file_path = os.path.join(shared_uploads_dir, f"{uuid.uuid4()}_{safe_filename[:50]}.txt")

        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Source URL: {url}\n\n{page_text}")
        
        # Use the existing task to process the file. This is efficient.
        tasks.process_document_task.delay(update.effective_chat.id, user_id, project_name, temp_file_path, 'txt')
        await update.message.reply_text(f"Successfully queued source from URL for processing. I'll let you know when it's added to project '{project_name}'.")

    except Exception as e:
        logger.error(f"Failed to add source from URL {url}: {e}")
        await update.message.reply_text(f"Failed to add source: {e}")