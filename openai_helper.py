import json
import os
import subprocess
import openai
from config import OPENAI_API_KEY, PRICING
from utils.files import get_audio_duration
from utils.functions import create_invoice

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

functions = [
    {
        "name": "create_invoice",
        "description": "Create a Tryton invoice with line items",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "The ID of the client (party) in Tryton"
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code, e.g., EUR or USD"
                },
                "items": {
                    "type": "array",
                    "description": "List of items in the invoice",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "quantity": {"type": "number"},
                            "price": {"type": "number"}
                        },
                        "required": ["product_id", "quantity", "price"]
                    }
                }
            },
            "required": ["client_id", "items"]
        }
    }
]


async def call_openai_function(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that helps manage invoices and financial tasks for a business. You use structured function calls to handle tasks like creating invoices."},
                {"role": "user", "content": message}
            ],
            tools=[
                {
                    "type": "function",
                    "function": func
                } for func in functions
            ],
            tool_choice="auto"
        )

        choice = response.choices[0]
        message = choice.message
        print(message)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                if func_name == "create_invoice":
                    return create_invoice(**arguments)

        return message.content or "Function executed, no response content."

    except Exception as e:
        return f"Error in function call: {e}"

async def ask_intention_function(prompt):
    result = await call_openai_function(prompt)
    cost = 0.0  # Replace with real token cost if needed
    return result, cost

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