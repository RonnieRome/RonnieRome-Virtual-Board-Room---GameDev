import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import traceback
from config.app_config import AppConfig


class LoggingService:
    def __init__(self):
        self.config = AppConfig
        self.logs_dir = self.config.BASE_DIR / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize different log files for different purposes
        self.app_logger = self._setup_logger('app', self.logs_dir / 'app.log')
        self.error_logger = self._setup_logger('error', self.logs_dir / 'error.log')
        self.access_logger = self._setup_logger('access', self.logs_dir / 'access.log')
        self.ai_logger = self._setup_logger('ai_services', self.logs_dir / 'ai_services.log')

        # Setup metric tracking
        self.metrics_file = self.logs_dir / 'metrics.json'
        self.metrics = self._load_metrics()

    def _setup_logger(self, name: str, log_file: Path) -> logging.Logger:
        """Configure a logger with specific settings."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)

        return logger

    def log_app_event(self, event_type: str, details: Dict[str, Any],
                      level: str = 'info') -> None:
        """Log application events with structured data."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }

        log_message = json.dumps(log_data)

        if level == 'error':
            self.app_logger.error(log_message)
        elif level == 'warning':
            self.app_logger.warning(log_message)
        else:
            self.app_logger.info(log_message)

    def log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """Log detailed error information with context."""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        self.error_logger.error(json.dumps(error_data))

    def log_access(self, user_id: str, resource: str, action: str,
                   status: str, details: Optional[Dict] = None) -> None:
        """Log access events for security and monitoring."""
        access_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'status': status,
            'details': details or {}
        }

        self.access_logger.info(json.dumps(access_data))

    def log_ai_interaction(self, service: str, model: str,
                           interaction_type: str, details: Dict[str, Any]) -> None:
        """Log AI service interactions with detailed metrics."""
        interaction_data = {
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'model': model,
            'type': interaction_type,
            'details': details
        }

        self.ai_logger.info(json.dumps(interaction_data))
        self._update_ai_metrics(service, model, details)

    def get_recent_errors(self, limit: int = 10) -> list:
        """Retrieve recent error logs."""
        errors = []
        try:
            with open(self.logs_dir / 'error.log', 'r', encoding='utf-8') as f:
                for line in f.readlines()[-limit:]:
                    try:
                        errors.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return errors

    def get_ai_service_metrics(self) -> Dict[str, Any]:
        """Get accumulated AI service usage metrics."""
        return self.metrics.get('ai_services', {})

    def _load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics from file."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.error_logger.error(f"Error loading metrics: {str(e)}")
        return {'ai_services': {}}

    def _save_metrics(self) -> None:
        """Save current metrics to file."""
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            self.error_logger.error(f"Error saving metrics: {str(e)}")

    def _update_ai_metrics(self, service: str, model: str, details: Dict) -> None:
        """Update AI service usage metrics."""
        if 'ai_services' not in self.metrics:
            self.metrics['ai_services'] = {}

        service_metrics = self.metrics['ai_services'].setdefault(service, {})
        model_metrics = service_metrics.setdefault(model, {
            'total_requests': 0,
            'total_tokens': 0,
            'total_errors': 0,
            'average_response_time': 0
        })

        # Update metrics
        model_metrics['total_requests'] += 1
        model_metrics['total_tokens'] += details.get('tokens', 0)

        if details.get('error'):
            model_metrics['total_errors'] += 1

        # Update average response time
        if 'response_time' in details:
            current_avg = model_metrics['average_response_time']
            total_requests = model_metrics['total_requests']
            new_time = details['response_time']
            model_metrics['average_response_time'] = (
                    (current_avg * (total_requests - 1) + new_time) / total_requests
            )

        self._save_metrics()

    def rotate_logs(self, max_size_mb: int = 10) -> None:
        """Rotate log files when they exceed the specified size."""
        for log_file in self.logs_dir.glob('*.log'):
            try:
                if log_file.stat().st_size > max_size_mb * 1024 * 1024:
                    # Create backup file with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = log_file.with_name(
                        f"{log_file.stem}_{timestamp}.log"
                    )
                    log_file.rename(backup_file)

                    # Create new empty log file
                    log_file.touch()

                    # Reinitialize loggers
                    logging.getLogger(log_file.stem).handlers = []
                    self._setup_logger(log_file.stem, log_file)
            except Exception as e:
                self.error_logger.error(f"Error rotating logs: {str(e)}")

    def cleanup_old_logs(self, days: int = 30) -> None:
        """Remove log files older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for log_file in self.logs_dir.glob('*.log.*'):
            try:
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
            except Exception as e:
                self.error_logger.error(f"Error cleaning up logs: {str(e)}")