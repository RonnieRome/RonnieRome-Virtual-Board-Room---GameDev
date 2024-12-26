from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import json
from collections import defaultdict
import statistics
from config.app_config import AppConfig


class AnalyticsService:
    def __init__(self):
        self.config = AppConfig
        self.analytics_dir = self.config.BASE_DIR / "analytics"
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        self.current_day = datetime.now().date()
        self.daily_metrics = self._load_daily_metrics()

    def track_conversation_metrics(self, conversation_id: str,
                                   metrics: Dict[str, Any]) -> None:
        """Track metrics for a specific conversation."""
        self._ensure_current_day()

        conversation_metrics = self.daily_metrics['conversations'].setdefault(
            conversation_id, {
                'message_count': 0,
                'total_tokens': 0,
                'ai_service_usage': defaultdict(int),
                'response_times': [],
                'error_count': 0
            }
        )

        # Update metrics
        conversation_metrics['message_count'] += 1
        conversation_metrics['total_tokens'] += metrics.get('tokens', 0)

        if 'ai_service' in metrics:
            conversation_metrics['ai_service_usage'][metrics['ai_service']] += 1

        if 'response_time' in metrics:
            conversation_metrics['response_times'].append(metrics['response_time'])

        if metrics.get('error'):
            conversation_metrics['error_count'] += 1

        self._save_daily_metrics()

    def track_file_metrics(self, file_data: Dict[str, Any]) -> None:
        """Track metrics for file operations."""
        self._ensure_current_day()

        file_metrics = self.daily_metrics['files']
        file_type = file_data.get('type', 'unknown')

        file_metrics['total_files'] = file_metrics.get('total_files', 0) + 1
        file_metrics['file_types'] = file_metrics.get('file_types', {})
        file_metrics['file_types'][file_type] = file_metrics['file_types'].get(file_type, 0) + 1

        if 'size' in file_data:
            file_metrics['total_size'] = file_metrics.get('total_size', 0) + file_data['size']

        self._save_daily_metrics()

    def track_ai_metrics(self, service: str, model: str,
                         metrics: Dict[str, Any]) -> None:
        """Track AI service usage metrics."""
        self._ensure_current_day()

        ai_metrics = self.daily_metrics['ai_services'].setdefault(service, {})
        model_metrics = ai_metrics.setdefault(model, {
            'request_count': 0,
            'total_tokens': 0,
            'response_times': [],
            'error_count': 0
        })

        model_metrics['request_count'] += 1
        model_metrics['total_tokens'] += metrics.get('tokens', 0)

        if 'response_time' in metrics:
            model_metrics['response_times'].append(metrics['response_time'])

        if metrics.get('error'):
            model_metrics['error_count'] += 1

        self._save_daily_metrics()

    def get_conversation_analytics(self, conversation_id: str,
                                   days: int = 7) -> Dict[str, Any]:
        """Get analytics for a specific conversation over time."""
        analytics = {
            'message_trends': [],
            'token_usage': [],
            'ai_service_distribution': defaultdict(int),
            'average_response_times': [],
            'error_rate': 0
        }

        metrics_files = self._get_recent_metric_files(days)
        total_messages = 0
        total_errors = 0

        for metrics_file in metrics_files:
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    daily_data = json.load(f)

                if conversation_id in daily_data.get('conversations', {}):
                    conv_data = daily_data['conversations'][conversation_id]
                    date = metrics_file.stem

                    analytics['message_trends'].append({
                        'date': date,
                        'count': conv_data['message_count']
                    })

                    analytics['token_usage'].append({
                        'date': date,
                        'tokens': conv_data['total_tokens']
                    })

                    total_messages += conv_data['message_count']
                    total_errors += conv_data['error_count']

                    for service, count in conv_data['ai_service_usage'].items():
                        analytics['ai_service_distribution'][service] += count

                    if conv_data['response_times']:
                        analytics['average_response_times'].append({
                            'date': date,
                            'time': statistics.mean(conv_data['response_times'])
                        })
            except Exception as e:
                print(f"Error processing metrics file {metrics_file}: {str(e)}")

        analytics['error_rate'] = (
            total_errors / total_messages if total_messages > 0 else 0
        )

        return analytics

    def get_system_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get system-wide analytics."""
        analytics = {
            'total_conversations': 0,
            'total_messages': 0,
            'total_tokens': 0,
            'file_metrics': {
                'total_files': 0,
                'file_types': defaultdict(int),
                'total_size': 0
            },
            'ai_service_metrics': defaultdict(lambda: {
                'total_requests': 0,
                'total_tokens': 0,
                'average_response_time': 0,
                'error_rate': 0
            })
        }

        metrics_files = self._get_recent_metric_files(days)

        for metrics_file in metrics_files:
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    daily_data = json.load(f)

                analytics['total_conversations'] += len(daily_data.get('conversations', {}))

                # Process conversation metrics
                for conv_data in daily_data.get('conversations', {}).values():
                    analytics['total_messages'] += conv_data['message_count']
                    analytics['total_tokens'] += conv_data['total_tokens']

                # Process file metrics
                file_metrics = daily_data.get('files', {})
                analytics['file_metrics']['total_files'] += file_metrics.get('total_files', 0)
                analytics['file_metrics']['total_size'] += file_metrics.get('total_size', 0)

                for file_type, count in file_metrics.get('file_types', {}).items():
                    analytics['file_metrics']['file_types'][file_type] += count

                # Process AI service metrics
                for service, service_data in daily_data.get('ai_services', {}).items():
                    for model, model_data in service_data.items():
                        service_metrics = analytics['ai_service_metrics'][service]
                        service_metrics['total_requests'] += model_data['request_count']
                        service_metrics['total_tokens'] += model_data['total_tokens']

                        if model_data['response_times']:
                            avg_time = statistics.mean(model_data['response_times'])
                            current_avg = service_metrics['average_response_time']
                            total_requests = service_metrics['total_requests']

                            service_metrics['average_response_time'] = (
                                    (current_avg * (total_requests - 1) + avg_time) / total_requests
                            )

                        if model_data['request_count'] > 0:
                            error_rate = model_data['error_count'] / model_data['request_count']
                            service_metrics['error_rate'] = (
                                    (service_metrics['error_rate'] + error_rate) / 2
                            )

            except Exception as e:
                print(f"Error processing metrics file {metrics_file}: {str(e)}")

        return analytics

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get summary of current day's metrics."""
        return {
            'conversations': len(self.daily_metrics['conversations']),
            'total_messages': sum(
                conv['message_count']
                for conv in self.daily_metrics['conversations'].values()
            ),
            'total_tokens': sum(
                conv['total_tokens']
                for conv in self.daily_metrics['conversations'].values()
            ),
            'files_processed': self.daily_metrics.get('files', {}).get('total_files', 0),
            'ai_services': {
                service: {
                    'requests': sum(
                        model['request_count'] for model in models.values()
                    )
                }
                for service, models in self.daily_metrics.get('ai_services', {}).items()
            }
        }

    def _load_daily_metrics(self) -> Dict[str, Any]:
        """Load metrics for current day."""
        metrics_file = self._get_current_metrics_file()

        if metrics_file.exists():
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading daily metrics: {str(e)}")

        return {
            'conversations': {},
            'files': {
                'total_files': 0,
                'file_types': {},
                'total_size': 0
            },
            'ai_services': {}
        }

    def _save_daily_metrics(self) -> None:
        """Save current day's metrics."""
        metrics_file = self._get_current_metrics_file()

        try:
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.daily_metrics, f, indent=2)
        except Exception as e:
            print(f"Error saving daily metrics: {str(e)}")

    def _ensure_current_day(self) -> None:
        """Check and update metrics for new day if needed."""
        today = datetime.now().date()
        if today != self.current_day:
            self.current_day = today
            self.daily_metrics = self._load_daily_metrics()

    def _get_current_metrics_file(self) -> Path:
        """Get path for current day's metrics file."""
        return self.analytics_dir / f"{self.current_day.isoformat()}.json"

    def _get_recent_metric_files(self, days: int) -> List[Path]:
        """Get list of metric files for specified number of recent days."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        return sorted([
            f for f in self.analytics_dir.glob('*.json')
            if start_date <= datetime.strptime(f.stem, '%Y-%m-%d').date() <= end_date
        ])

    def cleanup_old_metrics(self, days: int = 30) -> None:
        """Remove metric files older than specified number of days."""
        cutoff_date = datetime.now().date() - timedelta(days=days)

        for metrics_file in self.analytics_dir.glob('*.json'):
            try:
                file_date = datetime.strptime(metrics_file.stem, '%Y-%m-%d').date()
                if file_date < cutoff_date:
                    metrics_file.unlink()
            except Exception as e:
                print(f"Error cleaning up metrics file {metrics_file}: {str(e)}")