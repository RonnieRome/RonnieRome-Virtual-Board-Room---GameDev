# api_test.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

from dotenv import load_dotenv
import os

load_dotenv()
print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))
def send_to_gemini(self, conv_id, prompt, model="gemini-pro"):
    try:
        print("Preparing context for Gemini...")
        conversation = self.get_conversation(conv_id)
        context = self._get_conversation_context(conversation)
        full_prompt = f"Context:\n{context}\n\nUser: {prompt}"
        print(f"Sending request to Gemini with prompt: {full_prompt}")

        response = self.gemini.generate_content(full_prompt)
        print(f"Gemini response: {response}")

        tokens_in = self.estimate_tokens(prompt)
        tokens_out = self.estimate_tokens(response.text)

        self.add_message(conv_id, prompt, "user", "gemini", model, tokens_in)
        self.add_message(conv_id, response.text, "assistant", "gemini", model, tokens_out)
        return response.text
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Gemini Error: {str(e)}")
        return f"Error: {str(e)}"

import requests

try:
    response = requests.get("https://example.googleapis.com")  # Replace with the Gemini endpoint if possible
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
except Exception as e:
    print(f"Network error: {str(e)}")

import logging

# Set logging level to DEBUG to capture all HTTP requests and responses
logging.basicConfig(level=logging.DEBUG)

# Log HTTP traffic for urllib3 (used by many Python libraries, including requests)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

import google.generativeai as genai
from google.generativeai import GenerativeModel
import os

# Configure Google Gemini API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def test_gemini_simple():
    try:
        model = GenerativeModel("gemini-pro")  # Ensure model name is correct
        print("Gemini model configured successfully. Sending request...")

        # Test a basic prompt
        response = model.generate_content("Hello Gemini, just a connectivity test!")
        print(f"Response: {response.text}")

    except Exception as e:
        # Catch and print additional information for debugging
        import traceback
        traceback.print_exc()
        print(f"Gemini API Call Failed. Error: {e}")


# Run the test
test_gemini_simple()

import google.generativeai as genai

# Reconfigure API Key
genai.configure(api_key="YOUR_NEW_OR_EXISTING_API_KEY")

# Test connectivity
response = genai.generate_text(model="gemini-pro", prompt="Test Gemini connection.")
print(response)

