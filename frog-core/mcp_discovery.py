import os
import json
import logging
from typing import List, Dict, Any, Optional
from memory_manager import MemoryManager

logger = logging.getLogger("frog-mcp-discovery")

class MCPDiscovery:
    """
    Handles discovery and routing of MCP servers from a vectorized market.
    Currently uses a seeded list; future versions will scrape from community registries.
    """
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.collection_name = "mcp_market"

    def seed_initial_market(self):
        """Seeds the vector DB with known community MCP servers."""
        community_tools = [
            {
                "id": "mcp-server-sqlite",
                "name": "SQLite MCP",
                "description": "Read and write to local SQLite databases. Supports complex queries and schema inspection.",
                "image": "mcp/sqlite-server",
                "capabilities": ["read_query", "write_query", "list_tables", "describe_table"]
            },
            {
                "id": "mcp-server-postgres",
                "name": "PostgreSQL MCP",
                "description": "Connect to local or remote PostgreSQL databases. Execute SQL, manage schemas, and inspect data.",
                "image": "mcp/postgres-server",
                "capabilities": ["query", "execute", "list_schemas"]
            },
            {
                "id": "mcp-server-google-drive",
                "name": "Google Drive MCP",
                "description": "Access files, folders, and documents in Google Drive. Search, download, and upload files.",
                "image": "mcp/google-drive-server",
                "capabilities": ["search_files", "download_file", "upload_file"]
            },
            {
                "id": "mcp-server-slack",
                "name": "Slack MCP",
                "description": "Send messages, search history, and manage channels in Slack workspace.",
                "image": "mcp/slack-server",
                "capabilities": ["send_message", "search_messages", "list_channels"]
            },
            {
                "id": "mcp-server-github",
                "name": "GitHub MCP",
                "description": "Manage repositories, issues, pull requests, and code on GitHub.",
                "image": "mcp/github-server",
                "capabilities": ["list_issues", "create_pr", "search_code"]
            },
            {
                "id": "mcp-server-pdf",
                "name": "PDF Expert MCP",
                "description": "Extract text, images, and tables from PDF documents. Handle complex layouts and OCR.",
                "image": "mcp/pdf-server",
                "capabilities": ["extract_text", "extract_images", "read_metadata"]
            }
        ]
        
        try:
            for tool in community_tools:
                # Add to memory manager for semantic search
                # Ensure metadata values are primitives (ChromaDB requirement)
                metadata = tool.copy()
                if "capabilities" in metadata:
                    metadata["capabilities"] = json.dumps(metadata["capabilities"])
                
                self.memory_manager.add_memory(
                    collection_name=self.collection_name,
                    content=f"{tool['name']}: {tool['description']}",
                    metadata=metadata,
                    doc_id=tool['id']
                )
            logger.info(f"Successfully seeded {len(community_tools)} MCP servers into market.")
        except Exception as e:
            logger.error(f"Failed to seed MCP market: {e}")

    def find_tools_by_intent(self, intent: str, n_results: int = 2) -> List[Dict[str, Any]]:
        """Finds the most relevant MCP servers for a given user intent."""
        try:
            results = self.memory_manager.search_memory(
                collection_name=self.collection_name,
                query=intent,
                n_results=n_results
            )
            return [res['metadata'] for res in results]
        except Exception as e:
            logger.error(f"MCP discovery search failed: {e}")
            return []

    def list_market(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lists available tools in the market (unsorted/top-N)."""
        try:
            # We use an empty query or a placeholder to get top items if ChromaDB supports it
            # For simplicity in this prototype, we'll just search for a broad term
            results = self.memory_manager.search_memory(
                collection_name=self.collection_name,
                query="MCP tool", 
                n_results=limit
            )
            return [res['metadata'] for res in results]
        except Exception as e:
            logger.error(f"MCP market list failed: {e}")
            return []
