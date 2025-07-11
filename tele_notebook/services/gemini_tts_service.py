# tele_notebook/services/gemini_tts_service.py

import asyncio
from google import genai
from google.genai import types

from tele_notebook.core.config import settings
from tele_notebook.utils.audio_utils import convert_to_wav # We will need this again

def _blocking_generate_audio(script: str) -> bytes:
    """
    Makes the blocking API call to Gemini TTS using the older, client-based SDK pattern.
    This matches the provided example and will work with the installed library version.
    """
    # 1. Instantiate the client. The API key is used automatically from the environment.
    client = genai.Client()

    # 2. Define the model and contents payload, as per the example.
    model = "models/gemini-2.5-pro" # Using a standard text model to generate the audio modality
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=script)],
        ),
    ]

    # 3. Define the config to request audio output.
    # We will use a single, high-quality voice for simplicity, as the multi-speaker
    # configuration is complex and may not be fully supported in this older pattern
    # without SSML.
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Zephyr" # A high-quality standard voice
                )
            )
        ),
    )

    # 4. Call the streaming endpoint and collect the audio data chunks.
    audio_chunks = []
    mime_type = "audio/L16;rate=24000" # Default, in case we don't get it from the response

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is not None and
            chunk.candidates[0].content is not None and
            chunk.candidates[0].content.parts is not None and
            chunk.candidates[0].content.parts[0].inline_data and
            chunk.candidates[0].content.parts[0].inline_data.data
        ):
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            audio_chunks.append(inline_data.data)
            # Store the mime type from the first audio chunk
            if inline_data.mime_type:
                mime_type = inline_data.mime_type

    if not audio_chunks:
        raise ValueError("Failed to generate audio content. No audio data received from Gemini API.")

    # 5. Combine the chunks and create a proper WAV file.
    raw_audio_data = b"".join(audio_chunks)
    wav_audio_data = convert_to_wav(raw_audio_data, mime_type)
    
    return wav_audio_data

async def generate_podcast_audio(script: str, language: str) -> bytes:
    """
    Generates podcast audio from a script using Gemini's TTS model.
    """
    audio_bytes = await asyncio.to_thread(_blocking_generate_audio, script)
    return audio_bytes