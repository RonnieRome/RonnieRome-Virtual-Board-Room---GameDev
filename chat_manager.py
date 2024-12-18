import base64
import json
import os
import tiktoken
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
import openai
from anthropic import Anthropic
from dotenv import load_dotenv
from google.generativeai import GenerativeModel


class ChatHistoryManager:
    CLAUDE_MODELS = {
        "claude-3-sonnet-20240229": "Sonnet",
        "claude-3-opus-20240229": "Opus",
        "claude-3-haiku-20240307": "Haiku"
    }

    GPT_MODELS = {
        "gpt-4": "GPT-4",
        "gpt-3.5-turbo": "GPT-3.5"
    }

    GEMINI_MODELS = {
        "gemini-pro": "Gemini Pro"
    }

    DALLE_MODELS = {
        "dall-e-3": "DALL-E 3",
        "dall-e-2": "DALL-E 2"
    }

    def __init__(self):
        load_dotenv()
        #self.openai = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.gemini = GenerativeModel('gemini-pro')
        self.history_dir = Path("chat_histories")
        self.exports_dir = Path("exports")
        self.history_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        self.gpt_encoder = tiktoken.encoding_for_model("gpt-4")

    def create_conversation(self, title):
        conv_id = f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conv_path = self.history_dir / f"{conv_id}.json"
        conversation = {
            "title": title,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        self._save_conversation(conv_path, conversation)
        return conv_id

    def generate_image_dalle(self, conv_id, prompt, model="dall-e-3", size="1024x1024"):
        try:
            # Calculate DALL-E token equivalents
            dalle_prompt_tokens = self.estimate_tokens(prompt)  # Count actual prompt tokens
            dalle_image_tokens = 4000 if model == "dall-e-3" else 2000  # Base image generation tokens

            response = self.openai.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url

            # Download the image and convert to base64
            import requests
            image_data = requests.get(image_url).content
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            # Save the prompt message with actual token count
            self.add_message(conv_id, prompt, "user", "dalle", model, dalle_prompt_tokens)

            # Save the image message with generation token count
            image_message = {
                "content": f"Generated image for prompt: {prompt}",
                "image_data": image_b64,
                "sender": "assistant",
                "timestamp": datetime.now().isoformat(),
                "ai_service": "dalle",
                "model": model,
                "tokens": dalle_image_tokens
            }

            conversation = self.get_conversation(conv_id)
            conversation["messages"].append(image_message)
            self._save_conversation(self._get_conv_path(conv_id), conversation)

            return image_b64

        except Exception as e:
            #print(f"DALL-E Error: {str(e)}")
            return None

    def analyze_code(self, content, language, max_length=8000):
        truncated_content = content if len(content) <= max_length \
            else content[:max_length] + "\n...\n[Content Truncated]"
        analysis_prompt = f"""Analyze this {language} code:
```{language}
{truncated_content}
```
Provide a concise analysis covering:
1. Main functionality
2. Key components
3. Potential improvements or issues
4. Suggestions for enhancement"""
        try:
            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Analysis error: {str(e)}"

    def log_file_analysis(self, file_name, language, analysis_summary):
        log_file = Path("file_analysis_log.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            log_entry = f"[{datetime.now().isoformat()}] File: {file_name}, Language: {language}\nAnalysis:\n{analysis_summary}\n\n"
            f.write(log_entry)

    def add_message(self, conv_id, content, sender, ai_service=None, model=None, tokens=None):
        conv_path = self._get_conv_path(conv_id)
        conversation = self._load_conversation(conv_path)

        # If tokens not provided, estimate them
        if tokens is None:
            tokens = self.estimate_tokens(content)

        message = {
            "content": content,
            "sender": sender,
            "timestamp": datetime.now().isoformat(),
            "ai_service": ai_service,
            "model": model,
            "tokens": tokens
        }
        conversation["messages"].append(message)
        self._save_conversation(conv_path, conversation)

    def get_conversation(self, conv_id):
        try:
            return self._load_conversation(self._get_conv_path(conv_id))
        except Exception as e:
            print(f"Error getting conversation: {str(e)}")
            return None

    def list_conversations(self):
        try:
            # Get all conversation files
            conv_files = list(self.history_dir.glob("*.json"))

            # Create a list of tuples (conv_id, creation_time)
            conv_list = []
            for file in conv_files:
                try:
                    with open(file, encoding='utf-8') as f:
                        conv_data = json.load(f)
                        created_at = datetime.fromisoformat(conv_data.get('created_at', '2000-01-01T00:00:00'))
                        conv_list.append((file.stem, created_at))
                except Exception as e:
                    print(f"Error reading conversation {file}: {e}")
                    continue

            # Sort by creation time in descending order (newest first)
            conv_list.sort(key=lambda x: x[1], reverse=True)

            # Return just the conversation IDs in sorted order
            return [conv[0] for conv in conv_list]

        except Exception as e:
            print(f"Error listing conversations: {str(e)}")
            return []

    def send_to_claude(self, conv_id, prompt, model="claude-3-sonnet-20240229"):
        try:
            conversation = self.get_conversation(conv_id)
            context = self._get_conversation_context(conversation)

            system_prompt = "You're participating in a group chat. Previous messages are provided for context. Respond naturally."
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"

            response = self.anthropic.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": full_prompt}]
            )

            tokens_in = self.estimate_tokens(full_prompt)
            response_content = response.content[0].text
            tokens_out = self.estimate_tokens(response_content)

            self.add_message(conv_id, prompt, "user", "claude", model, tokens_in)
            self.add_message(conv_id, response_content, "assistant", "claude", model, tokens_out)
            return response_content

        except Exception as e:
            print(f"Claude Error: {str(e)}")
            return f"Error: {str(e)}"

    def send_to_chatgpt(self, conv_id, prompt, model="gpt-3.5-turbo"):
        try:
            conversation = self.get_conversation(conv_id)
            context = self._get_conversation_context(conversation)

            system_message = {"role": "system",
                              "content": "You're participating in a group chat. Previous messages are provided for context. Respond naturally."}
            user_message = {"role": "user", "content": f"Context:\n{context}\n\nUser: {prompt}"}

            response = self.openai.chat.completions.create(
                model=model,
                messages=[system_message, user_message]
            )

            tokens_in = self.estimate_tokens(prompt)
            response_content = response.choices[0].message.content
            tokens_out = self.estimate_tokens(response_content)

            self.add_message(conv_id, prompt, "user", "chatgpt", model, tokens_in)
            self.add_message(conv_id, response_content, "assistant", "chatgpt", model, tokens_out)
            return response_content

        except Exception as e:
            print(f"ChatGPT Error: {str(e)}")
            return f"Error: {str(e)}"

    def send_to_gemini(self, conv_id, prompt, model="gemini-pro"):
        try:
            conversation = self.get_conversation(conv_id)
            context = self._get_conversation_context(conversation)
            full_prompt = f"Context:\n{context}\n\nUser: {prompt}"

            response = self.gemini.generate_content(full_prompt)

            tokens_in = self.estimate_tokens(prompt)
            tokens_out = self.estimate_tokens(response.text)

            self.add_message(conv_id, prompt, "user", "gemini", model, tokens_in)
            self.add_message(conv_id, response.text, "assistant", "gemini", model, tokens_out)
            return response.text

        except Exception as e:
            print(f"Gemini Error: {str(e)}")
            return f"Error: {str(e)}"

    def export_conversation(self, conv_id, format="json"):
        conv = self.get_conversation(conv_id)
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        filename = f"{conv['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        export_path = export_dir / f"{filename}.{format}"

        if format == "json":
            content = json.dumps(conv, indent=2, ensure_ascii=False)
        else:
            content = ""
            for msg in conv["messages"]:
                ai_service = f"[{msg.get('ai_service', 'user')}]" if msg.get('ai_service') else ""
                content += f"{msg['sender']} {ai_service}: {msg['content']}\n\n"

        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return content

    def extract_code_messages(self, conv_id):
        conv = self.get_conversation(conv_id)
        return [(i, msg) for i, msg in enumerate(conv["messages"]) if "```" in msg["content"]]

    def export_selected_code(self, conv_id, selected_indices):
        export_dir = Path("code_exports")
        export_dir.mkdir(exist_ok=True)

        conv = self.get_conversation(conv_id)
        exported = []

        for i in selected_indices:
            msg = conv["messages"][i]
            if "```" in msg["content"]:
                start = msg["content"].find("```") + 3
                end = msg["content"].find("```", start)
                if end > start:
                    lang = msg["content"][start:msg["content"].find("\n", start)].strip()
                    code = msg["content"][msg["content"].find("\n", start):end].strip()

                    filename = f"snippet_{i}.{lang}"
                    path = export_dir / filename
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(code)
                    exported.append(path)
        return exported

    def estimate_tokens(self, text):
        try:
            return len(self.gpt_encoder.encode(str(text)))
        except Exception as e:
            print(f"Token estimation error: {e}")
            return 0

    def _get_conv_path(self, conv_id):
        return self.history_dir / f"{conv_id}.json"

    def _save_conversation(self, path, conversation):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)

    def _load_conversation(self, path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    def _get_conversation_context(self, conversation, last_n=10):
        messages = conversation['messages'][-last_n:]
        return "\n".join([
            f"{msg['sender']} ({msg.get('ai_service', 'user')}): {msg['content']}"
            for msg in messages
        ])