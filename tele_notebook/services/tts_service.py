import aiohttp
from tele_notebook.core.config import settings
from tele_notebook.utils.prompts import SUPPORTED_LANGUAGES

async def synthesize_audio(text: str, language: str) -> bytes:
    """Sends text to Piper TTS and returns the audio bytes."""
    voice_model = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES["en"])["voice"]
    url = f"{settings.PIPER_TTS_URL}?voice={voice_model}"
    
    # The 'ssl=False' parameter is the key change.
    # It explicitly tells aiohttp not to use or verify SSL for this request.
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=text.encode('utf-8'), ssl=False) as response:
            response.raise_for_status()
            return await response.read()