import openai
import os
from dotenv import load_dotenv

load_dotenv()  # Load the .env file

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_response(user_input, memory):
    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    for msg in memory:
        if "User:" in msg:
            messages.append({"role": "user", "content": msg.replace("User: ", "")})
        elif "AI:" in msg:
            messages.append({"role": "assistant", "content": msg.replace("AI: ", "")})

    messages.append({"role": "user", "content": user_input})

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    return response.choices[0].message.content.strip()
