from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class FileAnalysisResult:
    """Data class to store analysis results for a single file."""
    file_id: str
    file_name: str
    file_type: str
    content: str
    metadata: Dict[str, Any]
    summary: str
    dependencies: List[str]
    sections: Dict[str, Any]
    analysis_timestamp: str

@dataclass
class AIAnalysisContext:
    """Structured context for AI analysis."""
    files: Dict[str, Dict]
    relationships: Dict[str, List[str]]
    metadata: Dict[str, Any]
    timestamp: str