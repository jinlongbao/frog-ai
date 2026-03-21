def execute(params, context):
    prompt = params.get("prompt")
    input_type = params.get("input_type", "text")
    
    # We raise a special exception that the main orchestrator will catch
    # to trigger the HITL (Human-in-the-Loop) state saving logic.
    raise Exception(f"HITL_SIGNAL: {prompt} | TYPE: {input_type}")
