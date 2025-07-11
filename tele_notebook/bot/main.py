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
    
    # --- THIS IS THE FIX ---
    # We add read_timeout and write_timeout to make the connection more stable
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .read_timeout(30)  # Seconds to wait for a response from Telegram
        .write_timeout(30) # Seconds to wait to send a message to Telegram
        .build()
    )

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

    application.add_handler(CommandHandler("discover", handlers.discover))
    application.add_handler(CommandHandler("addsource", handlers.add_source))

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