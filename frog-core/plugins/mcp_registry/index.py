import os
import logging
from typing import Dict, Any, List

def execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search and install MCP servers from the community market.
    """
    action = params.get("action")
    query = params.get("query")
    tool_id = params.get("tool_id")
    
    mcp_discovery = context.get("mcp_discovery")
    docker_manager = context.get("docker_manager")
    mcp_manager = context.get("mcp_manager")
    
    if not mcp_discovery or not docker_manager or not mcp_manager:
        return {"status": "error", "message": "MCP Discovery, Docker Manager, or MCP Manager not found in context."}
    
    if action == "search":
        if not query:
            return {"status": "error", "message": "'query' is required for search."}
        
        tools = mcp_discovery.find_tools_by_intent(query)
        if not tools:
            return {"status": "success", "message": "No matching tools found in the community market.", "results": []}
        
        return {
            "status": "success", 
            "message": f"Found {len(tools)} potential tools. Use 'install' action with tool_id to activate one.",
            "results": tools
        }
    
    elif action == "install":
        if not tool_id:
            return {"status": "error", "message": "'tool_id' is required for install."}
        
        # 1. Find tool metadata
        # (For now, we'll search the discovery engine as a registry)
        tools = mcp_discovery.find_tools_by_intent(tool_id, n_results=1)
        if not tools or tools[0]['id'] != tool_id:
             return {"status": "error", "message": f"Tool '{tool_id}' not found in registry."}
        
        tool = tools[0]
        image = tool.get("image")
        
        if not image:
            return {"status": "error", "message": f"No Docker image specified for tool '{tool_id}'."}
            
        # 2. Spin up container (Async in real world, but here we'll just prep the command)
        # Note: In a production 'Frog', we'd use docker_manager.run_tool_container
        # but for MCP persistence, we want a long-running container.
        
        # Simplified for Prototype: 
        # We'll assume the container is started or we use 'exec' if already running.
        # In this phase, we'll just 'connect' using a mocked command that simulates the server.
        
        # Actual implementation would be:
        # container_id = docker_manager.start_service(image)
        # mcp_manager.connect(tool_id, ["docker", "exec", "-i", container_id, "python", "server.py"])
        
        success = mcp_manager.connect(tool_id, ["python", "-m", f"mcp_servers.{tool_id.replace('-', '_')}"]) # Mocked local command
        
        if success:
            return {
                "status": "success", 
                "message": f"Successfully initialized {tool['name']}. You can now use its capabilities.",
                "capabilities": tool.get("capabilities", [])
            }
        else:
            return {"status": "error", "message": f"Failed to connect to MCP server '{tool_id}'."}
            
    elif action == "list":
        active = mcp_manager.list_active_servers()
        return {"status": "success", "active_servers": active}
        
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}
