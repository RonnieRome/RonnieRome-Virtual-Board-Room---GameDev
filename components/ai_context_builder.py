import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from components.analysis_models import FileAnalysisResult, AIAnalysisContext



@dataclass
class AIAnalysisContext:
    """Structured context for AI analysis."""
    files: Dict[str, Dict]
    relationships: Dict[str, List[str]]
    metadata: Dict[str, Any]
    timestamp: str


class AIContextBuilder:
    """Builds context for AI analysis of files."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def build_context(self, analysis_results: Dict[str, FileAnalysisResult]) -> AIAnalysisContext:
        """
        Build a comprehensive context for AI analysis.
        """
        try:
            # Organize file information
            files = {}
            relationships = {}
            overall_metadata = {
                'total_files': len(analysis_results),
                'languages': set(),
                'shared_dependencies': set()
            }

            # Process each file's analysis results
            for file_id, result in analysis_results.items():
                # Store file information
                files[file_id] = {
                    'name': result.file_name,
                    'type': result.file_type,
                    'summary': result.summary,
                    'dependencies': result.dependencies,
                    'sections': self._summarize_sections(result.sections),
                    'metadata': result.metadata
                }

                # Track languages used
                overall_metadata['languages'].add(result.file_type)

                # Track relationships
                relationships[file_id] = self._find_related_files(
                    file_id,
                    result,
                    analysis_results
                )

                # Analyze shared dependencies
                if result.dependencies:
                    overall_metadata['shared_dependencies'].update(
                        set(result.dependencies)
                    )

            # Convert sets to lists for JSON serialization
            overall_metadata['languages'] = list(overall_metadata['languages'])
            overall_metadata['shared_dependencies'] = list(
                overall_metadata['shared_dependencies']
            )

            return AIAnalysisContext(
                files=files,
                relationships=relationships,
                metadata=overall_metadata,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            self.logger.error(f"Error building AI context: {str(e)}")
            raise

    def _summarize_sections(self, sections: Dict) -> Dict:
        """Create a concise summary of file sections for AI analysis."""
        summary = {}
        for section_name, content in sections.items():
            if isinstance(content, dict) and 'type' in content:
                summary[section_name] = {
                    'type': content['type'],
                    'name': content.get('name', ''),
                    'line_number': content.get('line_number', 0)
                }
        return summary

    def _find_related_files(
            self,
            current_file_id: str,
            current_result: FileAnalysisResult,
            all_results: Dict[str, FileAnalysisResult]
    ) -> List[str]:
        """
        Find files related to the current file based on:
        - Direct imports/dependencies
        - Shared dependencies
        - Similar functionality or purpose
        """
        related_files = []
        for other_id, other_result in all_results.items():
            if other_id != current_file_id:
                # Check for direct dependencies
                if self._has_dependency_relationship(current_result, other_result):
                    related_files.append(other_id)
                # Check for shared dependencies
                elif self._has_shared_dependencies(current_result, other_result):
                    related_files.append(other_id)
                # Check for similar functionality
                elif self._has_similar_functionality(current_result, other_result):
                    related_files.append(other_id)

        return related_files

    def _has_dependency_relationship(
            self,
            file1: FileAnalysisResult,
            file2: FileAnalysisResult
    ) -> bool:
        """Check if files have a direct dependency relationship."""
        return (
                file2.file_name in file1.dependencies or
                file1.file_name in file2.dependencies
        )

    def _has_shared_dependencies(
            self,
            file1: FileAnalysisResult,
            file2: FileAnalysisResult
    ) -> bool:
        """Check if files share common dependencies."""
        deps1 = set(file1.dependencies)
        deps2 = set(file2.dependencies)
        return bool(deps1.intersection(deps2))

    def _has_similar_functionality(
            self,
            file1: FileAnalysisResult,
            file2: FileAnalysisResult
    ) -> bool:
        """
        Check if files have similar functionality based on:
        - File type
        - Code structure
        - Common patterns
        """
        return (
                file1.file_type == file2.file_type and
                any(
                    pattern in file1.content and pattern in file2.content
                    for pattern in ['class', 'def', 'function', 'import']
                )
        )