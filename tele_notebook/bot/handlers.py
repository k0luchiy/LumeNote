# handlers.py

import os
import uuid
from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from tele_notebook.services import user_service
from tele_notebook.tasks import tasks
from tele_notebook.utils.prompts import SUPPORTED_LANGUAGES
# ADD THIS IMPORT
from tele_notebook.utils.localization import get_text

# Helper to get language code
def _get_lang(user_id: int) -> str:
    return user_service.get_user_state(user_id).get("language", "en")


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang_code = _get_lang(user.id)
    text = get_text("welcome", lang_code, user_mention=user.mention_markdown_v2())
    # Note: We pass the already-escaped mention, so we use reply_markdown_v2
    await update.message.reply_markdown_v2(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _get_lang(update.effective_user.id)
    text = get_text("help", lang_code)
    await update.message.reply_markdown_v2(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    
    project = escape_markdown(state.get('active_project', 'default'), version=2)
    current_lang_code = escape_markdown(state.get('language', 'en'), version=2)
    lang_name = escape_markdown(SUPPORTED_LANGUAGES.get(state.get('language', 'en'), {}).get('name', 'English'), version=2)

    text = get_text("status", lang_code, user_id=f"`{user_id}`", project=f"`{project}`", lang_name=f"`{lang_name}`", lang_code=f"`{current_lang_code}`")
    await update.message.reply_markdown_v2(text)

# --- Project Management Handlers ---

async def new_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    project_name = " ".join(context.args)
    if not project_name:
        text = get_text("provide_project_name", lang_code)
        await update.message.reply_markdown_v2(text)
        return

    user_service.set_user_state(user_id, project=project_name)
    text = get_text("project_created", lang_code, project_name=project_name)
    await update.message.reply_text(text)

async def list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    projects = user_service.get_user_projects(user_id)
    if not projects:
        text = get_text("no_projects", lang_code)
        await update.message.reply_markdown_v2(text)
        return
    
    project_list = "\n".join(f"\\- `{escape_markdown(p, version=2)}`" for p in projects)
    text = get_text("your_projects", lang_code, project_list=project_list)
    await update.message.reply_markdown_v2(text)

async def switch_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    project_name = " ".join(context.args)
    if not project_name:
        text = get_text("switch_provide_name", lang_code)
        await update.message.reply_markdown_v2(text)
        return

    existing_projects = user_service.get_user_projects(user_id)
    if project_name not in existing_projects:
        text = get_text("project_not_found", lang_code, project_name=project_name)
        await update.message.reply_text(text)
        return

    user_service.set_user_state(user_id, project=project_name)
    text = get_text("switched_project", lang_code, project_name=project_name)
    await update.message.reply_text(text)

# --- Language Handler ---

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supported_codes = ", ".join(f"`{key}`" for key in SUPPORTED_LANGUAGES.keys())
    if not context.args or context.args[0] not in SUPPORTED_LANGUAGES:
        # Use the user's CURRENT language for the error message
        lang_code = _get_lang(user_id)
        text = get_text("lang_usage", lang_code, supported_codes=supported_codes)
        await update.message.reply_markdown_v2(text)
        return
    
    new_lang_code = context.args[0]
    user_service.set_user_state(user_id, lang=new_lang_code)
    lang_name = SUPPORTED_LANGUAGES[new_lang_code]['name']
    # Use the NEW language for the confirmation message
    text = get_text("lang_set", new_lang_code, lang_name=lang_name)
    await update.message.reply_text(text)

# --- Core Feature Handlers ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")

    if not project_name or project_name == "default":
        text = get_text("create_project_first", lang_code)
        await update.message.reply_markdown_v2(text)
        return

    doc = update.message.document
    file_name_safe = escape_markdown(doc.file_name, version=2)
    file_ext = doc.file_name.split('.')[-1].lower()
    supported_types = ['pdf', 'txt', 'md']

    if file_ext not in supported_types:
        text = get_text("unsupported_file_type", lang_code, supported_types=', '.join(supported_types))
        await update.message.reply_text(text)
        return

    text = get_text("processing_file", lang_code, file_name=file_name_safe)
    await update.message.reply_markdown_v2(text)
    
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
        text = get_text("create_project_first", lang_code)
        await update.message.reply_markdown_v2(text)
        return

    existing_projects = user_service.get_user_projects(user_id)
    if not existing_projects or project_name not in existing_projects:
        text = get_text("no_documents_in_project", lang_code)
        await update.message.reply_markdown_v2(text)
        return

    text = get_text("thinking", lang_code)
    await update.message.reply_text(text)

    tasks.answer_question_task.delay(chat_id, user_id, project_name, question, lang_code)

async def generate_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, task_function, command_name: str):
    user_id = update.effective_user.id
    lang_code = _get_lang(user_id)
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    topic = " ".join(context.args)
    
    if not project_name or project_name == "default":
        text = get_text("select_project_first", lang_code)
        await update.message.reply_markdown_v2(text)
        return
    if not topic:
        text = get_text("provide_topic", lang_code, command_name=command_name)
        await update.message.reply_markdown_v2(text)
        return

    content_type = "podcast" if task_function == tasks.generate_podcast_task else "mind map"
    text = get_text("generating_content", lang_code, content_type=content_type, topic=escape_markdown(topic, version=2))
    await update.message.reply_markdown_v2(text)

    task_function.delay(update.effective_chat.id, user_id, project_name, topic, lang_code)