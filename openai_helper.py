import os
import subprocess
import openai
from config import OPENAI_API_KEY, PRICING
from utils.files import get_audio_duration

client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ Correct OpenAI client setup

async def ask_openai(prompt):

    try:
        response = client.chat.completions.create(  # ✅ New API format
            model="chatgpt-4o-latest",  # Change to "gpt-3.5-turbo" if needed
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        # Extract token usage from OpenAI response
        tokens_used = response.usage.total_tokens
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        # Calculate cost
        cost = (input_tokens * PRICING["gpt-4-turbo"]["input"]) + (output_tokens * PRICING["gpt-4-turbo"]["output"])

        return [response.choices[0].message.content, cost]  # ✅ Correct way to access response

    except Exception as e:
        return f"Error: {e}"


def transcribe(wav_path):
    with open(wav_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        audio_duration = get_audio_duration(wav_path)
        cost = audio_duration * PRICING["whisper-1"]["audio"]
        return transcript.text, cost


def create_voice_out_of_text(message_id,text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )

    character_count = len(text)
    cost = (character_count / 1000) * PRICING["tts-1"]["audio"]
    if response.content is None:
        print("❌ Failed to generate audio.")
        return
        # Define a dynamic directory for saving audio files
    output_dir = os.path.join(os.getcwd(), "downloads")  # Saves in a 'downloads' folder
    os.makedirs(output_dir, exist_ok=True)  # Ensure directory exists

    # Create a unique filename based on message ID
    output_filename = f"speech_{message_id}.mp3"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, "wb") as audio_file:
        audio_file.write(response.content)

        # Create a unique filename
        mp3_filename = f"speech_{message_id}.mp3"
        mp3_path = os.path.join(output_dir, mp3_filename)

    # Convert MP3 to OGG (Opus format for Telegram voice messages)
    ogg_filename = f"speech_{message_id}.ogg"
    ogg_path = os.path.join(output_dir, ogg_filename)

    subprocess.run([
        "/opt/homebrew/bin/ffmpeg", "-i", mp3_path,  # Input MP3 file
        "-c:a", "libopus",  # Use Opus codec
        "-b:a", "32k",  # Set bitrate (adjustable, 32k is Telegram standard)
        "-ar", "48000",  # Sample rate required for Telegram voice messages
        "-ac", "1",  # Mono audio
        "-y", ogg_path  # Output file
    ], check=True)

    return ogg_path, cost