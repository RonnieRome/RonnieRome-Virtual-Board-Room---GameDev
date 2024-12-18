import json, tiktoken
from datetime import datetime
from pathlib import Path
import openai
from anthropic import Anthropic
import google.generativeai as genai
from google.generativeai import GenerativeModel
from dotenv import load_dotenv
import os


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

    def __init__(self):
        load_dotenv()
        self.openai = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.gemini = GenerativeModel('gemini-pro')
        self.history_dir = Path("chat_histories")
        self.history_dir.mkdir(exist_ok=True)
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
        """
           Logs metadata and analysis summary for uploaded files to a central log file for reference.
           """
        log_file = Path("file_analysis_log.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            log_entry = f"[{datetime.now().isoformat()}] File: {file_name}, Language: {language}\nAnalysis:\n{analysis_summary}\n\n"
            f.write(log_entry)


    def add_message(self, conv_id, content, sender, ai_service=None, model=None, tokens=None):
        conv_path = self._get_conv_path(conv_id)
        conversation = self._load_conversation(conv_path)
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
            return [file.stem for file in self.history_dir.glob("*.json")]
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