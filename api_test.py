# api_test.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

def test_apis():
    # Test OpenAI
    try:
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        openai_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}]
        )
        print("OpenAI Test:", openai_response.choices[0].message.content)
    except Exception as e:
        print("OpenAI Error:", str(e))

    # Test Anthropic
    try:
        anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        anthropic_response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": "test"}]
        )
        print("Claude Test:", anthropic_response.content[0].text)
    except Exception as e:
        print("Claude Error:", str(e))

if __name__ == "__main__":
    test_apis()