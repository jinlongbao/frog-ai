def execute(params: dict, context: dict) -> dict:
    """
    Plugin to manage expert knowledge.
    params: { action: "save", title: "...", content: "...", tags: [...] }
    context: { save_expert_knowledge: sync function }
    """
    action = params.get("action")
    save_fn = context.get("save_expert_knowledge")
    
    if not save_fn:
        return {"status": "error", "message": "Knowledge saving service unavailable."}
        
    if action == "save":
        title = params.get("title")
        content = params.get("content")
        tags = params.get("tags", [])
        
        if not title or not content:
            return {"status": "error", "message": "Title and Content are required."}
            
        try:
            # Call the sync-friendly helper from context
            result = save_fn(title=title, content=content, tags=tags)
            return {
                "status": "success", 
                "message": "Knowledge saved successfully to the expert knowledge base.", 
                "filename": result.get("filename")
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to save knowledge: {str(e)}"}
            
    return {"status": "error", "message": f"Unknown action: {action}"}
