import json
import subprocess
import threading
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("frog-mcp-manager")

class MCPClient:
    """
    JSON-RPC 2.0 client for communicating with MCP servers via stdio.
    """
    def __init__(self, command: List[str]):
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.pending_requests: Dict[str, threading.Event] = {}
        self.responses: Dict[str, Any] = {}
        self._stop_event = threading.Event()
        self._read_thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the MCP server process and the reading thread."""
        logger.info(f"Starting MCP server: {' '.join(self.command)}")
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        self._read_thread = threading.Thread(target=self._listen, daemon=True)
        self._read_thread.start()

    def _listen(self):
        """Background thread to read JSON-RPC responses from stdout."""
        while not self._stop_event.is_set() and self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if not line:
                break
            
            try:
                data = json.loads(line)
                if "id" in data:
                    req_id = str(data["id"])
                    self.responses[req_id] = data
                    if req_id in self.pending_requests:
                        self.pending_requests[req_id].set()
                elif "method" in data:
                    # Handle notifications/requests from server (optional)
                    pass
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode line from MCP server: {line}")

    def call(self, method: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Calls a JSON-RPC method on the server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server is not running.")
            
        req_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        
        event = threading.Event()
        self.pending_requests[req_id] = event
        
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        if event.wait(timeout):
            response = self.responses.pop(req_id)
            self.pending_requests.pop(req_id)
            if "error" in response:
                raise RuntimeError(f"MCP Error: {response['error']}")
            return response.get("result", {})
        else:
            self.pending_requests.pop(req_id)
            raise TimeoutError(f"MCP request {req_id} timed out after {timeout}s")

    def stop(self):
        """Stops the MCP server and cleanup."""
        self._stop_event.set()
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

class MCPManager:
    """
    Manages multiple active MCP server connections.
    """
    def __init__(self):
        self.active_clients: Dict[str, MCPClient] = {}

    def connect(self, server_id: str, command: List[str]) -> bool:
        if server_id in self.active_clients:
            return True
        try:
            client = MCPClient(command)
            client.start()
            self.active_clients[server_id] = client
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_id}: {e}")
            return False

    def get_client(self, server_id: str) -> Optional[MCPClient]:
        return self.active_clients.get(server_id)

    def list_active_servers(self) -> List[str]:
        return list(self.active_clients.keys())

    def close_all(self):
        for client in self.active_clients.values():
            client.stop()
        self.active_clients.clear()
