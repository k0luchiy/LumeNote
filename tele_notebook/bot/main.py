import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from tele_notebook.core.config import settings
from tele_notebook.bot import handlers
from tele_notebook.utils import localization # <-- ADD THIS IMPORT

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def main() -> None:
    """Run the bot."""
    localization.load_translations()
    logger.info("Starting bot...")
    
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("status", handlers.status))
    
    # Project Management
    application.add_handler(CommandHandler("newproject", handlers.new_project))
    application.add_handler(CommandHandler("listprojects", handlers.list_projects))
    application.add_handler(CommandHandler("switchproject", handlers.switch_project))

    # Language
    application.add_handler(CommandHandler("lang", handlers.set_language))

    # Content Generation (using the generic handler)
    application.add_handler(CommandHandler(
        "podcast", lambda u, c: handlers.generate_content_handler(u, c, handlers.tasks.generate_podcast_task, "podcast")
    ))
    application.add_handler(CommandHandler(
        "mindmap", lambda u, c: handlers.generate_content_handler(u, c, handlers.tasks.generate_mindmap_task, "mindmap")
    ))

    # Message Handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()