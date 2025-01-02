import ast
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from components.analysis_models import FileAnalysisResult, AIAnalysisContext
from components.ai_context_builder import AIContextBuilder

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """Service for analyzing file content and relationships."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_results: Dict[str, FileAnalysisResult] = {}
        self.file_relationships: Dict[str, List[str]] = {}
        self.context_builder = AIContextBuilder()
        self.analysis_cache = {}

    def get_ai_context(self) -> AIAnalysisContext:
        """Get the current context prepared for AI analysis."""
        return self.context_builder.build_context(self.analysis_results)

    def analyze_file_batch(self, files: List[Dict]) -> Dict[str, FileAnalysisResult]:
        """
        Analyze multiple files and build AI context.

        Args:
            files: List of dictionaries containing file data

        Returns:
            Dictionary mapping file IDs to their analysis results
        """
        try:
            results = {}
            for file_data in files:
                analysis = self.analyze_single_file(file_data)
                results[analysis.file_id] = analysis

            self.analysis_results.update(results)
            self._analyze_file_relationships()

            return results

        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            raise

    def analyze_single_file(self, file_data: Dict) -> FileAnalysisResult:
        """
        Analyze a single file and extract relevant information.

        Args:
            file_data: Dictionary containing file information and content

        Returns:
            FileAnalysisResult containing the analysis
        """
        try:
            file_type = self._determine_file_type(file_data)
            content = file_data.get('content', '')
            file_id = self._generate_file_id(file_data)

            # Check cache first
            cached_result = self._get_cached_analysis(content, file_type)
            if cached_result:
                return cached_result

            # Generate metadata and analysis
            metadata = self._generate_metadata(file_data, file_type)
            sections = self._create_file_sections(content, file_type)
            summary = self._generate_summary(content, file_type)
            dependencies = self._identify_dependencies(content, file_type)

            # Create analysis result
            analysis = FileAnalysisResult(
                file_id=file_id,
                file_name=file_data['name'],
                file_type=file_type,
                content=content,
                metadata=metadata,
                summary=summary,
                dependencies=dependencies,
                sections=sections,
                analysis_timestamp=datetime.now().isoformat()
            )

            # Cache the results
            self._cache_analysis(content, file_type, analysis)
            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing file {file_data.get('name', 'unknown')}: {str(e)}")
            raise

    def _determine_file_type(self, file_data: Dict) -> str:
        """Determine file type based on extension and content analysis."""
        extension = Path(file_data['name']).suffix.lower()

        type_map = {
            '.py': 'python',
            '.pyw': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown'
        }

        return type_map.get(extension, 'text')

    def _generate_metadata(self, file_data: Dict, file_type: str) -> Dict:
        """Generate metadata specific to file type."""
        metadata = {
            'size': len(file_data.get('content', '')),
            'created_at': file_data.get('stored_at', datetime.now().isoformat()),
            'file_type': file_type,
            'encoding': file_data.get('encoding', 'utf-8')
        }

        if file_type == 'python':
            metadata.update(self._analyze_python_metadata(file_data['content']))
        elif file_type in ['javascript', 'typescript']:
            metadata.update(self._analyze_js_metadata(file_data['content']))

        return metadata

    def _analyze_python_metadata(self, content: str) -> Dict[str, Any]:
        """Analyze Python code to extract metadata about its structure."""
        try:
            metadata = {
                'classes': [],
                'functions': [],
                'imports': [],
                'global_variables': []
            }

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        metadata['imports'].extend(n.name for n in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        for n in node.names:
                            metadata['imports'].append(f"{module}.{n.name}")
                    elif isinstance(node, ast.ClassDef):
                        class_info = {
                            'name': node.name,
                            'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                            'line_number': node.lineno
                        }
                        metadata['classes'].append(class_info)
                    elif isinstance(node, ast.FunctionDef):
                        func_info = {
                            'name': node.name,
                            'args': [arg.arg for arg in node.args.args],
                            'line_number': node.lineno,
                            'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                        }
                        metadata['functions'].append(func_info)
                    elif isinstance(node, ast.Assign) and all(
                            isinstance(target, ast.Name) for target in node.targets
                    ):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                metadata['global_variables'].append({
                                    'name': target.id,
                                    'line_number': node.lineno
                                })

                return metadata

            except SyntaxError as e:
                return {
                    'error': f"Syntax error in Python code: {str(e)}",
                    'partial_analysis': metadata
                }

        except Exception as e:
            self.logger.error(f"Error in Python metadata analysis: {str(e)}")
            return {'error': str(e)}

    def _analyze_js_metadata(self, content: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code to extract metadata."""
        return {
            'type': 'javascript',
            'size': len(content),
            'analysis_status': 'pending'
        }

    def _create_file_sections(self, content: str, file_type: str) -> Dict[str, Any]:
        """Create navigable sections based on file content and type."""
        sections = {
            'main': content,
            'segments': {}
        }

        if file_type == 'python':
            sections['segments'] = self._create_python_sections(content)
        elif file_type in ['javascript', 'typescript']:
            sections['segments'] = self._create_js_sections(content)

        return sections

    def _create_python_sections(self, content: str) -> Dict[str, Any]:
        """Create navigable sections for Python code."""
        sections = {}
        try:
            tree = ast.parse(content)
            current_class = None

            def get_node_source(node, lines):
                return '\n'.join(lines[node.lineno - 1:
                                       (node.end_lineno if hasattr(node, 'end_lineno') else node.lineno)])

            content_lines = content.split('\n')

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    current_class = node.name
                    sections[f"class_{node.name}"] = {
                        'type': 'class',
                        'name': node.name,
                        'content': get_node_source(node, content_lines),
                        'line_number': node.lineno,
                        'methods': {}
                    }
                elif isinstance(node, ast.FunctionDef):
                    if current_class and getattr(node, 'parent_node', None) == current_class:
                        sections[f"class_{current_class}"]['methods'][node.name] = {
                            'type': 'method',
                            'name': node.name,
                            'content': get_node_source(node, content_lines),
                            'line_number': node.lineno
                        }
                    else:
                        sections[f"function_{node.name}"] = {
                            'type': 'function',
                            'name': node.name,
                            'content': get_node_source(node, content_lines),
                            'line_number': node.lineno
                        }

            return sections

        except Exception as e:
            self.logger.error(f"Error creating Python sections: {str(e)}")
            return {'error': str(e)}

    def _create_js_sections(self, content: str) -> Dict[str, Any]:
        """Create navigable sections for JavaScript/TypeScript code."""
        return {
            'main': content,
            'sections': {}
        }

    def _generate_summary(self, content: str, file_type: str) -> str:
        """Generate a summary of the file content."""
        lines = content.split('\n')
        return f"File contains {len(lines)} lines of {file_type} code"

    def _identify_dependencies(self, content: str, file_type: str) -> List[str]:
        """Identify file dependencies based on imports and references."""
        dependencies = []
        if file_type == 'python':
            for line in content.split('\n'):
                if line.strip().startswith(('import ', 'from ')):
                    dependencies.append(line.strip())
        return dependencies

    def _analyze_file_relationships(self) -> None:
        """Analyze relationships between files in the current batch."""
        for file_id, analysis in self.analysis_results.items():
            related_files = []
            for other_id, other_analysis in self.analysis_results.items():
                if file_id != other_id:
                    if self._files_are_related(analysis, other_analysis):
                        related_files.append(other_id)
            self.file_relationships[file_id] = related_files

    def _files_are_related(self, analysis1: FileAnalysisResult,
                           analysis2: FileAnalysisResult) -> bool:
        """Determine if two files are related based on their content and dependencies."""
        return (analysis2.file_name in analysis1.content or
                analysis1.file_name in analysis2.content or
                any(dep in analysis2.content for dep in analysis1.dependencies))

    def _generate_file_id(self, file_data: Dict) -> str:
        """Generate a unique ID for a file."""
        return f"{file_data['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _get_decorator_name(self, decorator_node) -> str:
        """Extract decorator name from AST node."""
        if isinstance(decorator_node, ast.Name):
            return decorator_node.id
        elif isinstance(decorator_node, ast.Call):
            if isinstance(decorator_node.func, ast.Name):
                return decorator_node.func.id
        return "unknown_decorator"

    def _get_cached_analysis(self, content: str, file_type: str) -> Optional[FileAnalysisResult]:
        """Try to get cached analysis results."""
        cache_key = self._get_cache_key(content, file_type)
        return self.analysis_cache.get(cache_key)

    def _cache_analysis(self, content: str, file_type: str, result: FileAnalysisResult) -> None:
        """Cache analysis results."""
        cache_key = self._get_cache_key(content, file_type)
        self.analysis_cache[cache_key] = result

    def _get_cache_key(self, content: str, file_type: str) -> str:
        """Generate a cache key for file content."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{file_type}_{content_hash}"

    def get_file_relationships(self) -> Dict[str, List[str]]:
        """Get the relationships between files."""
        return self.file_relationships

    def get_file_analysis(self, file_id: str) -> Optional[FileAnalysisResult]:
        """Get analysis results for a specific file."""
        return self.analysis_results.get(file_id)

    def clear_analysis_cache(self):
        """Clear the analysis cache."""
        self.analysis_cache.clear()