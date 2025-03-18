import openai
from config import OPENAI_API_KEY

client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ Correct OpenAI client setup

async def ask_openai(prompt):
    print("here")  # Debugging statement

    try:
        response = client.chat.completions.create(  # ✅ New API format
            model="chatgpt-4o-latest",  # Change to "gpt-3.5-turbo" if needed
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        return response.choices[0].message.content  # ✅ Correct way to access response

    except Exception as e:
        return f"Error: {e}"