from typing import Dict, Optional, Callable, Any
from datetime import datetime
import asyncio
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
from config.app_config import AppConfig


class TaskManager:
    def __init__(self):
        self.config = AppConfig
        self.task_queue = Queue()
        self.results = {}
        self.tasks_dir = self.config.BASE_DIR / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._start_worker()

    def submit_task(self, task_type: str, task_data: Dict,
                    callback: Optional[Callable] = None) -> str:
        """Submit a task for background processing."""
        task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        task = {
            'id': task_id,
            'type': task_type,
            'data': task_data,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'callback': callback
        }

        self._save_task(task)
        self.task_queue.put(task)
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the current status of a task."""
        task_path = self.tasks_dir / f"{task_id}.json"

        if not task_path.exists():
            return None

        try:
            with open(task_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading task status: {str(e)}")
            return None

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a completed task."""
        return self.results.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.get_task_status(task_id)
        if not task or task['status'] != 'pending':
            return False

        task['status'] = 'cancelled'
        self._save_task(task)
        return True

    def _start_worker(self) -> None:
        """Start the background worker thread."""

        def worker():
            while True:
                task = self.task_queue.get()
                if task is None:
                    break

                try:
                    self._process_task(task)
                except Exception as e:
                    print(f"Error processing task {task['id']}: {str(e)}")
                    task['status'] = 'error'
                    task['error'] = str(e)
                    self._save_task(task)
                finally:
                    self.task_queue.task_done()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _process_task(self, task: Dict) -> None:
        """Process a single task."""
        task['status'] = 'processing'
        task['started_at'] = datetime.now().isoformat()
        self._save_task(task)

        try:
            # Handle different task types
            if task['type'] == 'file_processing':
                result = self._process_file_task(task['data'])
            elif task['type'] == 'ai_service':
                result = self._process_ai_task(task['data'])
            elif task['type'] == 'export':
                result = self._process_export_task(task['data'])
            else:
                raise ValueError(f"Unknown task type: {task['type']}")

            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()
            self.results[task['id']] = result

            # Call callback if provided
            if task['callback']:
                task['callback'](result)

        except Exception as e:
            task['status'] = 'error'
            task['error'] = str(e)
            task['completed_at'] = datetime.now().isoformat()

        self._save_task(task)

    def _process_file_task(self, data: Dict) -> Dict:
        """Process file-related tasks."""
        task_type = data.get('task_type')

        if task_type == 'analysis':
            return self._analyze_file(data)
        elif task_type == 'conversion':
            return self._convert_file(data)
        elif task_type == 'export':
            return self._export_file(data)
        else:
            raise ValueError(f"Unknown file task type: {task_type}")

    def _process_ai_task(self, data: Dict) -> Dict:
        """Process AI service-related tasks."""
        service = data.get('service')

        if service == 'claude':
            return self._process_claude_task(data)
        elif service == 'chatgpt':
            return self._process_chatgpt_task(data)
        elif service == 'dalle':
            return self._process_dalle_task(data)
        elif service == 'gemini':
            return self._process_gemini_task(data)
        else:
            raise ValueError(f"Unknown AI service: {service}")

    def _process_export_task(self, data: Dict) -> Dict:
        """Process export-related tasks."""
        export_type = data.get('export_type')

        if export_type == 'conversation':
            return self._export_conversation(data)
        elif export_type == 'code':
            return self._export_code(data)
        elif export_type == 'images':
            return self._export_images(data)
        else:
            raise ValueError(f"Unknown export type: {export_type}")

    def _save_task(self, task: Dict) -> None:
        """Save task data to disk."""
        task_path = self.tasks_dir / f"{task['id']}.json"

        try:
            # Create a copy without the callback function
            task_data = task.copy()
            task_data.pop('callback', None)

            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2)
        except Exception as e:
            print(f"Error saving task data: {str(e)}")

    # Placeholder methods for specific task processing
    def _analyze_file(self, data: Dict) -> Dict:
        """Analyze a file's content."""
        # Implement file analysis logic
        pass

    def _convert_file(self, data: Dict) -> Dict:
        """Convert a file to different format."""
        # Implement file conversion logic
        pass

    def _export_file(self, data: Dict) -> Dict:
        """Export a file with specific options."""
        # Implement file export logic
        pass

    def _process_claude_task(self, data: Dict) -> Dict:
        """Process Claude API requests."""
        # Implement Claude API interaction
        pass

    def _process_chatgpt_task(self, data: Dict) -> Dict:
        """Process ChatGPT API requests."""
        # Implement ChatGPT API interaction
        pass

    def _process_dalle_task(self, data: Dict) -> Dict:
        """Process DALL-E API requests."""
        # Implement DALL-E API interaction
        pass

    def _process_gemini_task(self, data: Dict) -> Dict:
        """Process Gemini API requests."""
        # Implement Gemini API interaction
        pass

    def _export_conversation(self, data: Dict) -> Dict:
        """Export conversation data."""
        # Implement conversation export logic
        pass

    def _export_code(self, data: Dict) -> Dict:
        """Export code snippets."""
        # Implement code export logic
        pass

    def _export_images(self, data: Dict) -> Dict:
        """Export images from conversation."""
        # Implement image export logic
        pass