import docker
import os
import uuid
import time
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("frog-docker")

class DockerManager:
    """
    Manages the lifecycle of Docker containers for Frog AI tools and MCP servers.
    Supports sibling container execution (requires /var/run/docker.sock mount).
    """
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.network_name = "frog-network"
            self._ensure_network()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    def _ensure_network(self):
        """Ensures the frog-network bridge exists."""
        if not self.client: return
        try:
            self.client.networks.get(self.network_name)
        except docker.errors.NotFound:
            self.client.networks.create(self.network_name, driver="bridge")

    def run_tool_container(self, 
                           image: str, 
                           command: str, 
                           volumes: Optional[Dict[str, Dict]] = None,
                           environment: Optional[Dict[str, str]] = None,
                           name_prefix: str = "frog-tool",
                           remove: bool = True,
                           timeout: int = 60) -> Dict[str, Any]:
        """
        Runs a command in a new container and returns the output.
        """
        if not self.client:
            return {"status": "error", "message": "Docker client not initialized"}

        container_name = f"{name_prefix}-{str(uuid.uuid4().hex)[:8]}"
        
        try:
            container = self.client.containers.run(
                image=image,
                command=command,
                name=container_name,
                volumes=volumes or {},
                environment=environment or {},
                network=self.network_name,
                detach=True,
                stdout=True,
                stderr=True
            )

            # Wait for completion with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                container.reload()
                if container.status == 'exited':
                    break
                time.sleep(0.5)
            
            if container.status != 'exited':
                container.kill()
                logs = container.logs().decode("utf-8")
                return {"status": "error", "message": f"Timeout after {timeout}s", "logs": logs}

            # Collect results
            exit_code = container.attrs['State']['ExitCode']
            logs = container.logs().decode("utf-8")
            
            if remove:
                container.remove()

            return {
                "status": "success" if exit_code == 0 else "error",
                "exit_code": exit_code,
                "output": logs
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_python_script(self, script_content: str, requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Runs a snippet of Python code in an isolated container.
        """
        # Create a temp file to mount
        temp_dir = "/tmp/frog-sandbox"
        os.makedirs(temp_dir, exist_ok=True)
        task_id = str(uuid.uuid4().hex)[:8]
        script_path = os.path.join(temp_dir, f"sandbox_{task_id}.py")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Build command
        cmd = ["python", f"/app/sandbox_{task_id}.py"]
        if requirements:
            req_str = " ".join(requirements)
            cmd = ["sh", "-c", f"pip install {req_str} && python /app/sandbox_{task_id}.py"]

        # Run
        result = self.run_tool_container(
            image="python:3.11-slim",
            command=" ".join(cmd) if isinstance(cmd, list) else cmd,
            volumes={
                os.path.abspath(script_path): {"bind": f"/app/sandbox_{task_id}.py", "mode": "ro"},
                "frog-pip-cache": {"bind": "/root/.cache/pip", "mode": "rw"}
            },
            name_prefix="frog-python"
        )
        
        # Cleanup host temp file
        try: os.remove(script_path)
        except: pass
        
        return result

# Global instance
docker_manager = DockerManager()
