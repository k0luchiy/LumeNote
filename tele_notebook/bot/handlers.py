import os
import uuid
from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from tele_notebook.services import user_service
from tele_notebook.tasks import tasks
from tele_notebook.utils.prompts import SUPPORTED_LANGUAGES
from tele_notebook.services import rag_service, llm_service

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr"Hi {user.mention_markdown_v2()}\! Welcome to the AI Notebook Bot\." +
        "\n\n*Here's how to get started:*\n"
        r"1\. Create a project with `/newproject <name>`" + "\n"
        r"2\. Upload `.pdf`, `.txt`, or `.md` files to it\." + "\n"
        r"3\. Ask questions about your documents\!" + "\n\n"
        r"Use /help to see all commands\."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        "*Available Commands:*\n"
        r"`/newproject <name>` \- Create a new project\." + "\n"
        r"`/listprojects` \- See all your projects\." + "\n"
        r"`/switchproject <name>` \- Switch to an existing project\." + "\n"
        r"`/podcast <topic>` \- Generate a podcast on a topic\." + "\n"
        r"`/mindmap <topic>` \- Generate a mind map image\." + "\n"
        r"`/lang <en\|ru\|de>` \- Set the response language\." + "\n"
        r"`/status` \- Check your current project and language\."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_service.get_user_state(user_id)
    project = escape_markdown(state.get('active_project', 'None'), version=2)
    lang_code = escape_markdown(state.get('language', 'en'), version=2)
    lang_name = escape_markdown(SUPPORTED_LANGUAGES.get(lang_code, {}).get('name', 'English'), version=2)

    await update.message.reply_markdown_v2(
        f"*Current Status:*\n"
        f"👤 User ID: `{user_id}`\n"
        f"🗂️ Active Project: `{project}`\n"
        f"🌐 Language: `{lang_name} ({lang_code})`"
    )

# --- Project Management Handlers ---

async def new_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    project_name = " ".join(context.args)
    if not project_name:
        await update.message.reply_markdown_v2(r"Please provide a name\. Usage: `/newproject <name>`")
        return

    user_service.set_user_state(user_id, project=project_name)
    await update.message.reply_text(f"Project '{project_name}' created and set as active.")

async def list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    projects = user_service.get_user_projects(user_id)
    if not projects:
        await update.message.reply_markdown_v2(r"You have no projects yet\. Create one with `/newproject <name>`\.")
        return
    
    project_list = "\n".join(f"\\- `{escape_markdown(p, version=2)}`" for p in projects)
    message = f"*Your projects:*\n{project_list}"
    await update.message.reply_markdown_v2(message)

async def switch_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    project_name = " ".join(context.args)
    if not project_name:
        await update.message.reply_markdown_v2(r"Please provide a name\. Usage: `/switchproject <name>`")
        return

    existing_projects = user_service.get_user_projects(user_id)
    if project_name not in existing_projects:
        await update.message.reply_text(f"Project '{project_name}' not found. Use /listprojects to see your projects.")
        return

    user_service.set_user_state(user_id, project=project_name)
    await update.message.reply_text(f"Switched to project '{project_name}'.")

# --- Language Handler ---

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supported_codes = ", ".join(f"`{key}`" for key in SUPPORTED_LANGUAGES.keys())
    if not context.args or context.args[0] not in SUPPORTED_LANGUAGES:
        await update.message.reply_markdown_v2(
            r"Usage: `/lang <lang_code>`" + f"\nSupported codes: {supported_codes}"
        )
        return
    
    lang_code = context.args[0]
    user_service.set_user_state(user_id, lang=lang_code)
    lang_name = SUPPORTED_LANGUAGES[lang_code]['name']
    await update.message.reply_text(f"Language set to {lang_name}.")

# --- Core Feature Handlers ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")

    if not project_name or project_name == "default":
        await update.message.reply_markdown_v2(r"Please create a project first with `/newproject <name>`\.")
        return

    doc = update.message.document
    file_name_safe = escape_markdown(doc.file_name, version=2)
    file_ext = doc.file_name.split('.')[-1].lower()
    supported_types = ['pdf', 'txt', 'md']

    if file_ext not in supported_types:
        await update.message.reply_text(f"Sorry, I only support {', '.join(supported_types)} files for now.")
        return

    await update.message.reply_markdown_v2(
        fr"Got it\! Processing `{file_name_safe}`\. I'll let you know when it's done\. This might take a moment\.\.\."
    )

    # --- THIS IS THE CORRECTED PART ---
    # Save the file to the SHARED volume path
    shared_uploads_dir = "/app/uploads"
    os.makedirs(shared_uploads_dir, exist_ok=True)
    temp_file_path = f"{shared_uploads_dir}/{uuid.uuid4()}_{doc.file_name}"
    # ------------------------------------
    
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(temp_file_path)

    tasks.process_document_task.delay(update.effective_chat.id, user_id, project_name, temp_file_path, file_ext)
    
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    language = state.get("language", "en")
    question = update.message.text
    chat_id = update.effective_chat.id

    if not project_name or project_name == "default":
        await update.message.reply_markdown_v2(r"Please create a project first with `/newproject <name>`\.")
        return

    existing_projects = user_service.get_user_projects(user_id)
    if not existing_projects or project_name not in existing_projects:
        await update.message.reply_markdown_v2(r"Your active project has no documents\. Please upload a file first\.")
        return

    # Give immediate feedback to the user
    await update.message.reply_text("🤔 Thinking...")

    # Offload the work to the Celery worker
    tasks.answer_question_task.delay(chat_id, user_id, project_name, question, language)

async def generate_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, task_function, command_name: str):
    user_id = update.effective_user.id
    state = user_service.get_user_state(user_id)
    project_name = state.get("active_project")
    language = state.get("language", "en")
    topic = " ".join(context.args)
    topic_safe = escape_markdown(topic, version=2)

    if not project_name or project_name == "default":
        await update.message.reply_markdown_v2(r"Please select a project first with `/switchproject <name>`\.")
        return
    if not topic:
        await update.message.reply_markdown_v2(fr"Please provide a topic\. Usage: `/{command_name} <your topic>`")
        return

    content_type = "podcast" if task_function == tasks.generate_podcast_task else "mind map"
    await update.message.reply_markdown_v2(
        fr"On it\! Generating your {content_type} about *{topic_safe}*\. This can take a minute\.\.\."
    )

    task_function.delay(update.effective_chat.id, user_id, project_name, topic, language)