from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
import json
import base64
from config.app_config import AppConfig


class DocumentManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.config = AppConfig
        self.base_dir = base_dir or self.config.BASE_DIR
        self.documents_dir = self.base_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def store_document(self, document_data: Dict, conversation_id: str) -> str:
        """Store a document with metadata and return its identifier."""
        document_id = f"{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        metadata = {
            'id': document_id,
            'conversation_id': conversation_id,
            'created_at': datetime.now().isoformat(),
            'name': document_data.get('name'),
            'type': document_data.get('type'),
            'language': document_data.get('language')
        }

        document_path = self.documents_dir / f"{document_id}.json"

        try:
            with open(document_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': metadata,
                    'content': document_data.get('content'),
                    'format': document_data.get('format')
                }, f, indent=2)

            return document_id

        except Exception as e:
            raise Exception(f"Error storing document: {str(e)}")

    def get_document(self, document_id: str) -> Optional[Dict]:
        """Retrieve a document by its identifier."""
        document_path = self.documents_dir / f"{document_id}.json"

        if not document_path.exists():
            return None

        try:
            with open(document_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")

    def get_conversation_documents(self, conversation_id: str) -> List[Dict]:
        """Retrieve all documents associated with a conversation."""
        documents = []

        for doc_path in self.documents_dir.glob(f"{conversation_id}_*.json"):
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    document = json.load(f)
                    documents.append(document)
            except Exception as e:
                print(f"Error loading document {doc_path}: {str(e)}")
                continue

        return sorted(documents, key=lambda x: x['metadata']['created_at'])

    def update_document_metadata(self, document_id: str, metadata_updates: Dict) -> bool:
        """Update document metadata."""
        document = self.get_document(document_id)
        if not document:
            return False

        document['metadata'].update(metadata_updates)
        document_path = self.documents_dir / f"{document_id}.json"

        try:
            with open(document_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2)
            return True
        except Exception as e:
            print(f"Error updating document metadata: {str(e)}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        document_path = self.documents_dir / f"{document_id}.json"

        if not document_path.exists():
            return False

        try:
            document_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
            return False

    def get_document_content(self, document_id: str) -> Optional[Union[str, bytes]]:
        """Retrieve the content of a document."""
        document = self.get_document(document_id)
        if not document:
            return None

        content = document.get('content')
        if document['metadata']['type'] == 'image':
            return base64.b64decode(content)
        return content

    def search_documents(self, conversation_id: str, query: str) -> List[Dict]:
        """Search for documents in a conversation based on metadata and content."""
        documents = self.get_conversation_documents(conversation_id)
        query = query.lower()

        matching_documents = []
        for doc in documents:
            # Search in metadata
            metadata_str = json.dumps(doc['metadata']).lower()
            if query in metadata_str:
                matching_documents.append(doc)
                continue

            # Search in content if it's text
            if doc['metadata']['type'] == 'text':
                if query in doc['content'].lower():
                    matching_documents.append(doc)

        return matching_documents

    def get_document_summary(self, document_id: str) -> Dict:
        """Generate a summary of document metadata and content preview."""
        document = self.get_document(document_id)
        if not document:
            return {}

        summary = {
            'id': document['metadata']['id'],
            'name': document['metadata']['name'],
            'type': document['metadata']['type'],
            'created_at': document['metadata']['created_at'],
            'size': len(str(document['content'])),
            'preview': None
        }

        if document['metadata']['type'] == 'text':
            # Get first 100 characters as preview
            summary['preview'] = document['content'][:100] + '...'
        elif document['metadata']['type'] == 'image':
            summary['preview'] = '[Image]'

        return summary