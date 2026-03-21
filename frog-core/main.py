from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import shutil
import zipfile
import io
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai
import httpx
import traceback

import asyncio
import logging

from orchestrator import orchestrator, TaskStatus
from tool_writer import tool_writer

app = FastAPI(title="Frog AI Brain")

# Track idleness for Phase 7 Autonomous Evolution
last_activity_time = datetime.now()

def update_activity():
    global last_activity_time
    last_activity_time = datetime.now()

async def curiosity_loop():
    print("[Curiosity] Background loop started.")
    while True:
        await asyncio.sleep(60)
        idle_time = (datetime.now() - last_activity_time).total_seconds()
        
        # Trigger if idle for > 3 minutes (180 seconds)
        if idle_time > 180:
            print(f"[Curiosity] System idle for {idle_time}s. Triggering Proactive Ghost Task...")
            update_activity() # Reset to prevent spam
            
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("[Curiosity] No OPENAI_API_KEY. Sleeping.")
                continue
                
            ghost_prompt = (
                "You are currently operating in Autonomous Idle Mode. "
                "There is no user prompt. "
                "Task: Read project_memory, identify a skill or knowledge gap, use search_browser to learn about it, "
                "and save the insights to knowledge_manager. Do NOT ask for human input."
            )
            
            payload = {
                "messages": [{"role": "user", "content": ghost_prompt}],
                "api_key": api_key,
                "model": os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
                "provider": "openai"
            }
            
            try:
                # Fire and forget locally
                async with httpx.AsyncClient(timeout=300) as client:
                    await client.post("http://127.0.0.1:8000/chat", json=payload)
                print("[Curiosity] Ghost Task completed.")
            except Exception as e:
                print(f"[Curiosity] Ghost Task failed: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(curiosity_loop())

def create_safe_openai_client(api_key: str, base_url: str = None):
    """
    创建一个安全的 OpenAI 客户端，避免 proxies 参数问题
    """
    client_kwargs = {
        "api_key": api_key
    }
    
    if base_url:
        client_kwargs["base_url"] = base_url
    
    http_client = httpx.Client(
        follow_redirects=True,
        timeout=120.0
    )
    client_kwargs["http_client"] = http_client
    
    return OpenAI(**client_kwargs)

# Enable CORS for the Node.js shell
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Knowledge storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
WEB_KNOWLEDGE_DIR = os.path.join(BASE_DIR, "web_knowledge")
EXPERT_KNOWLEDGE_DIR = os.path.join(BASE_DIR, "expert_knowledge")
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")
GENERATED_TOOLS_DIR = os.path.join(BASE_DIR, "generated_tools")

if not os.path.exists(KNOWLEDGE_DIR):
    os.makedirs(KNOWLEDGE_DIR)
if not os.path.exists(WEB_KNOWLEDGE_DIR):
    os.makedirs(WEB_KNOWLEDGE_DIR)
if not os.path.exists(EXPERT_KNOWLEDGE_DIR):
    os.makedirs(EXPERT_KNOWLEDGE_DIR)
if not os.path.exists(PLUGINS_DIR):
    os.makedirs(PLUGINS_DIR)
if not os.path.exists(GENERATED_TOOLS_DIR):
    os.makedirs(GENERATED_TOOLS_DIR)

class SearchQuery(BaseModel):
    query: str
    max_results: int = 5

class WebLearnRequest(BaseModel):
    url: str
    title: str = ""

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-3.5-turbo"
    reasoning_effort: str = "medium"
    provider: str = "openai"

class KnowledgeDeleteRequest(BaseModel):
    filename: str
    type: str # 'document' or 'web'

class ExpertKnowledge(BaseModel):
    title: str
    content: str
    tags: list[str] = []

class KnowledgeRetrieveRequest(BaseModel):
    query: str
    top_k: int = 3

@app.get("/")
async def root():
    return {"status": "online", "message": "Frog AI Brain is thinking..."}

@app.get("/health")
async def health():
    return {"status": "ok"}

async def categorize_document_background(file_path: str, filename: str):
    """
    Reads the first 1000 characters of a document via LLM to generate auto-tags and meta information.
    Saves to KNOWLEDGE_DIR/meta_{filename}.json
    """
    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return
            
        # Read snippets
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2000)
            
        client = create_safe_openai_client(api_key, os.getenv("OPENAI_BASE_URL"))
        prompt = f"Categorize the following document excerpt. Provide 1 to 3 relevant tags (e.g. Code, Guide, API, Story) separated by commas. Respond ONLY with the tags.\n\n{content}"
        
        response = client.chat.completions.create(
            model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.3
        )
        
        tags = [t.strip() for t in response.choices[0].message.content.split(",")]
        meta_data = {
            "filename": filename,
            "tags": tags,
            "auto_categorized": True,
            "created": datetime.now().isoformat()
        }
        
        meta_path = os.path.join(KNOWLEDGE_DIR, f"meta_{filename}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Auto-categorization failed for {filename}: {e}")

# Agent Factory: Ingest documents and "learn"
@app.post("/agent/generate")
async def generate_agent(files: list[UploadFile] = File(...)):
    saved_files = []
    for file in files:
        filename = getattr(file, "filename", "unknown.txt")
        file_path = os.path.join(KNOWLEDGE_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_files.append(filename)
        
        # Trigger Auto-categorization
        asyncio.create_task(categorize_document_background(file_path, filename))
    
    print(f"Ingested {len(saved_files)} files: {saved_files}")
    
    return {
        "status": "success",
        "message": f"Successfully ingested {len(saved_files)} documents with auto-categorization.",
        "files": saved_files,
        "persona": "Professional Business Assistant"
    }

# Get learned document content list
@app.get("/agent/knowledge")
async def get_agent_knowledge():
    files = []
    if os.path.exists(KNOWLEDGE_DIR):
        for filename in os.listdir(KNOWLEDGE_DIR):
            file_path = os.path.join(KNOWLEDGE_DIR, filename)
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    return {
        "status": "success",
        "count": len(files),
        "files": sorted(files, key=lambda x: x["created"], reverse=True)
    }

# Web Search: Search the internet for information
@app.post("/web/search")
async def web_search(search_query: SearchQuery):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(
                search_query.query,
                max_results=search_query.max_results
            ):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        
        return {
            "status": "success",
            "query": search_query.query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Fetch and save web content
@app.post("/web/learn")
async def web_learn(learn_request: WebLearnRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(learn_request.url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        title = learn_request.title or soup.title.string if soup.title else "Untitled"
        text_content = soup.get_text(separator="\n", strip=True)
        
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_content = "\n".join(chunk for chunk in chunks if chunk)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).rstrip()
        filename = f"{timestamp}_{safe_title[:50]}.txt"
        file_path = os.path.join(WEB_KNOWLEDGE_DIR, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {title}\n")
            f.write(f"URL: {learn_request.url}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(clean_content)
        
        return {
            "status": "success",
            "message": "Web content saved successfully",
            "title": title,
            "url": learn_request.url,
            "filename": filename,
            "content_length": len(clean_content)
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process content: {str(e)}")

# Get learned web content list
@app.get("/web/knowledge")
async def get_web_knowledge():
    files = []
    if os.path.exists(WEB_KNOWLEDGE_DIR):
        for filename in os.listdir(WEB_KNOWLEDGE_DIR):
            if filename.endswith(".txt"):
                file_path = os.path.join(WEB_KNOWLEDGE_DIR, filename)
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
    return {
        "status": "success",
        "count": len(files),
        "files": sorted(files, key=lambda x: x["created"], reverse=True)
    }

@app.post("/knowledge/delete")
async def delete_knowledge(req: KnowledgeDeleteRequest):
    try:
        target_dir = KNOWLEDGE_DIR if req.type == "document" else WEB_KNOWLEDGE_DIR
        file_path = os.path.join(target_dir, req.filename)
        
        # Security: prevent directory traversal
        if not os.path.abspath(file_path).startswith(os.path.abspath(target_dir)):
            raise HTTPException(status_code=400, detail="Invalid filename")
            
        if os.path.exists(file_path):
            os.remove(file_path)
            
            # Auto-cleanup related meta files if document
            if req.type == "document":
                meta_path = os.path.join(target_dir, f"meta_{req.filename}.json")
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                    
            return {"status": "success", "message": f"Deleted {req.filename}"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/expert/list")
async def get_expert_knowledge():
    files = []
    if os.path.exists(EXPERT_KNOWLEDGE_DIR):
        for filename in os.listdir(EXPERT_KNOWLEDGE_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        files.append({
                            "filename": filename,
                            "title": data.get("title", filename),
                            "tags": data.get("tags", []),
                            "created": data.get("created", datetime.fromtimestamp(os.stat(file_path).st_ctime).isoformat())
                        })
                except:
                    pass
    return {
        "status": "success",
        "count": len(files),
        "files": sorted(files, key=lambda x: x.get("created", ""), reverse=True)
    }

@app.post("/expert/retrieve")
async def retrieve_expert_knowledge(req: KnowledgeRetrieveRequest):
    results = []
    query = req.query.lower()
    
    if os.path.exists(EXPERT_KNOWLEDGE_DIR):
        for filename in os.listdir(EXPERT_KNOWLEDGE_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", "").lower()
                        content = data.get("content", "").lower()
                        tags = [t.lower() for t in data.get("tags", [])]
                        
                        score = 0
                        if query in title: score += 10
                        if any(query in t for t in tags): score += 5
                        if query in content: score += 1
                        
                        if score > 0:
                            results.append({
                                "title": data.get("title", ""),
                                "content": data.get("content", ""),
                                "tags": data.get("tags", []),
                                "score": score
                            })
                except:
                    pass
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return {
        "status": "success",
        "results": results[:req.top_k]
    }

# Chat with LLM
@app.post("/chat")
async def chat_with_llm(chat_request: ChatRequest):
    try:
        update_activity()
        load_dotenv()
        
        if not chat_request.api_key:
            raise HTTPException(status_code=400, detail="API key is required")
        
        if chat_request.provider == "gemini":
            genai.configure(api_key=chat_request.api_key)
            
            model = genai.GenerativeModel(chat_request.model)
            
            chat_history = []
            system_prompt = ""
            
            for msg in chat_request.messages:
                if msg.role == "system":
                    system_prompt = msg.content
                elif msg.role == "user":
                    chat_history.append({"role": "user", "parts": [msg.content]})
                elif msg.role == "assistant":
                    chat_history.append({"role": "model", "parts": [msg.content]})
            
            full_prompt = system_prompt + "\n\n" if system_prompt else ""
            if len(chat_history) > 0:
                last_msg = chat_history[-1]
                full_prompt += last_msg["parts"][0]
                chat_history = chat_history[:-1]
            
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(full_prompt)
            
            return {
                "status": "success",
                "message": response.text,
                "model": chat_request.model
            }
        else:
            api_key = chat_request.api_key or os.getenv("OPENAI_API_KEY")
            base_url = chat_request.base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            
            client = create_safe_openai_client(api_key, base_url)
            
            chat_params = {
                "model": chat_request.model,
                "messages": chat_request.messages,
                "temperature": 0.7
            }
            
            if chat_request.reasoning_effort and chat_request.model and ("o1" in chat_request.model.lower() or "o3" in chat_request.model.lower()):
                chat_params["reasoning_effort"] = chat_request.reasoning_effort
            
            response = client.chat.completions.create(**chat_params)
            
            return {
                "status": "success",
                "message": response.choices[0].message.content,
                "model": chat_request.model
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

# Save expert knowledge
@app.post("/expert/save")
async def save_expert_knowledge(knowledge: ExpertKnowledge):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in knowledge.title if c.isalnum() or c in (" ", "-", "_")).rstrip()
        filename = f"{timestamp}_{safe_title[:50]}.json"
        file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
        
        knowledge_data = {
            "title": knowledge.title,
            "content": knowledge.content,
            "tags": knowledge.tags,
            "created_at": datetime.now().isoformat()
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(knowledge_data, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "message": "Expert knowledge saved successfully",
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save knowledge: {str(e)}")

# Retrieve relevant expert knowledge
@app.post("/expert/retrieve")
async def retrieve_expert_knowledge(request: KnowledgeRetrieveRequest):
    try:
        query_words = set(request.query.lower().split())
        results = []
        
        if os.path.exists(EXPERT_KNOWLEDGE_DIR):
            for filename in os.listdir(EXPERT_KNOWLEDGE_DIR):
                if filename.endswith(".json"):
                    file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            
                            content = data.get("content", "").lower()
                            title = data.get("title", "").lower()
                            tags = [t.lower() for t in data.get("tags", [])]
                            
                            match_count = 0
                            for word in query_words:
                                if word in content or word in title or word in tags:
                                    match_count += 1
                            
                            if match_count > 0:
                                results.append({
                                    "title": data.get("title", ""),
                                    "content": data.get("content", ""),
                                    "tags": data.get("tags", []),
                                    "created_at": data.get("created_at", ""),
                                    "match_score": match_count
                                })
                    except Exception:
                        continue
        
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return {
            "status": "success",
            "count": len(results[:request.top_k]),
            "results": results[:request.top_k]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge: {str(e)}")

# Get all expert knowledge list
@app.get("/expert/list")
async def get_expert_list():
    files = []
    if os.path.exists(EXPERT_KNOWLEDGE_DIR):
        for filename in os.listdir(EXPERT_KNOWLEDGE_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        stat = os.stat(file_path)
                        files.append({
                            "filename": filename,
                            "title": data.get("title", ""),
                            "tags": data.get("tags", []),
                            "size": stat.st_size,
                            "created": data.get("created_at", datetime.fromtimestamp(stat.st_ctime).isoformat())
                        })
                except Exception:
                    continue
    
    return {
        "status": "success",
        "count": len(files),
        "files": sorted(files, key=lambda x: x["created"], reverse=True)
    }

class DeleteKnowledgeRequest(BaseModel):
    filename: str
    type: str  # "document" or "web"

class ResumeTaskRequest(BaseModel):
    user_input: str

@app.post("/knowledge/delete")
async def delete_knowledge(request: DeleteKnowledgeRequest):
    try:
        if request.type == "document":
            file_dir = KNOWLEDGE_DIR
        elif request.type == "web":
            file_dir = WEB_KNOWLEDGE_DIR
        else:
            raise HTTPException(status_code=400, detail="Invalid knowledge type")
        
        file_path = os.path.join(file_dir, request.filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        os.remove(file_path)
        
        return {
            "status": "success",
            "message": f"Successfully deleted {request.filename}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# Task Orchestration APIs
class CreateTaskRequest(BaseModel):
    messages: list[ChatMessage]
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-3.5-turbo"
    reasoning_effort: str = "medium"
    provider: str = "openai"
    webhook_url: str | None = None

@app.post("/task/create")
async def create_task(request: CreateTaskRequest):
    try:
        config = {
            "api_key": request.api_key,
            "base_url": request.base_url,
            "model": request.model,
            "reasoning_effort": request.reasoning_effort,
            "provider": request.provider,
            "webhook_url": request.webhook_url
        }
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Log user messages for persona inference
        try:
            from persona_manager import append_conversation_turn
            for msg in messages:
                if msg["role"] == "user":
                    append_conversation_turn("user", msg["content"])
        except Exception:
            pass
        
        task_id = orchestrator.create_task(messages, config)
        task = orchestrator.get_task(task_id)
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.get("/task/{task_id}")
async def get_task(task_id: str):
    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task_dict = task.to_dict()
    if task.status == TaskStatus.WAITING_FOR_HUMAN:
        task_dict["status"] = "WAITING_HUMAN_INPUT"
        task_dict["human_input_prompt"] = task.human_input_pending
    return task_dict

@app.post("/task/{task_id}/resume")
async def resume_task(task_id: str, request: ResumeTaskRequest):
    try:
        success = orchestrator.resume_task_with_human_input(task_id, request.user_input)
        if not success:
            raise HTTPException(status_code=400, detail="Task not found or not waiting for human input")
        
        task = orchestrator.get_task(task_id)
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume task: {str(e)}")

@app.post("/task/{task_id}/step")
async def execute_task_step(task_id: str):
    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status == TaskStatus.COMPLETED:
        task_dict = task.to_dict()
        task_dict["status"] = "COMPLETED"
        task_dict["final_answer"] = task.final_result
        return task_dict
    
    if task.status == TaskStatus.WAITING_FOR_HUMAN:
        task_dict = task.to_dict()
        task_dict["status"] = "WAITING_HUMAN_INPUT"
        task_dict["human_input_message"] = task.human_input_pending
        return task_dict
    
    try:
        load_dotenv()
        
        task.status = TaskStatus.THINKING
        
        react_system_prompt = orchestrator.build_react_prompt(task)
        
        messages = [{"role": "system", "content": react_system_prompt}] + task.messages
        
        provider = task.config.get("provider", "openai")
        if provider == "gemini":
            genai.configure(api_key=task.config["api_key"])
            model = genai.GenerativeModel(
                model_name=task.config["model"],
                generation_config={"temperature": 0.1}
            )
            
            # STABLE: Manual prompt construction to bypass library-specific 'prompt()' errors
            # This is the most robust way across SDK versions
            full_prompt_text = ""
            for msg in messages:
                role_label = "User" if msg["role"] == "user" else ("Assistant" if msg["role"] == "assistant" else "System Instruction")
                full_prompt_text += f"{role_label}: {msg['content']}\n\n"
            
            full_prompt_text += "Assistant:"
            
            response = model.generate_content(full_prompt_text)
            llm_response = response.text
        else:
            api_key = task.config["api_key"] or os.getenv("OPENAI_API_KEY")
            base_url = task.config["base_url"] or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            
            client = create_safe_openai_client(api_key, base_url)
            
            # Robust message merging for compatible endpoints
            compat_messages = []
            if task.messages:
                # 1. System Instruction is ALWAYS the first message (merged with first user msg)
                first_user_msg = task.messages[0]["content"] if task.messages[0]["role"] == "user" else ""
                compat_messages.append({
                    "role": "user",
                    "content": f"SYSTEM INSTRUCTION (CRITICAL):\n{react_system_prompt}\n\nUSER REQUEST:\n{first_user_msg}" if first_user_msg else react_system_prompt
                })
                
                # 2. Add intermediate messages
                if len(task.messages) > 1:
                    compat_messages.extend(task.messages[1:-1])
                    
                    # 3. Add the LAST message with a RECT reminder if it's from user
                    last_msg = task.messages[-1]
                    if last_msg["role"] == "user":
                        compat_messages.append({
                            "role": "user",
                            "content": f"{last_msg['content']}\n\n(IMPORTANT: Start your response with 'Thought:')"
                        })
                    else:
                        compat_messages.append(last_msg)
            else:
                compat_messages.append({"role": "user", "content": f"{react_system_prompt}\n\n(IMPORTANT: Start your response with 'Thought:')"})

            chat_params = {
                "model": task.config["model"],
                "messages": compat_messages,
                "temperature": 0.1
            }
            
            model_name = task.config["model"].lower()
            if task.config["reasoning_effort"] and ("o1" in model_name or "o3" in model_name):
                chat_params["reasoning_effort"] = task.config["reasoning_effort"]
            
            response = client.chat.completions.create(**chat_params)
            llm_response = response.choices[0].message.content
        
        # PERSIST: Add assistant's response to history
        task.messages.append({"role": "assistant", "content": llm_response})
        
        parsed = orchestrator.execute_step(task, llm_response)
        
        task_dict = task.to_dict()
        
        if parsed["type"] == "final_answer":
            task_dict["status"] = "COMPLETED"
            task_dict["final_answer"] = parsed["content"]
            return task_dict
        else:
            current_step = None
            observation = None
            
            if parsed.get("thought"):
                current_step = {
                    "type": "thought",
                    "content": parsed.get("thought", "")
                }
                task_dict["current_step"] = current_step
            
            if parsed.get("action"):
                tool_name = parsed.get("action", "")
                tool_params = parsed.get("action_input", {})
                
                current_step = {
                    "type": "action",
                    "tool_name": tool_name,
                    "params": tool_params
                }
                task_dict["current_step"] = current_step
                
                try:
                    if not isinstance(tool_params, dict):
                        tool_params = {}

                    if tool_name == "search_browser":
                        search_query = tool_params.get("command", "") or tool_params.get("query", "")
                        if search_query:
                            results = []
                            import time
                            for attempt in range(2):
                                try:
                                    with DDGS() as ddgs:
                                        results = list(ddgs.text(search_query, max_results=5))
                                    if results: break
                                except Exception as e:
                                    if attempt == 0: time.sleep(1)
                                    else: raise e
                            
                            observation = {
                                "type": "observation",
                                "tool": "search_browser",
                                "content": results if results else "No results found."
                            }
                        else:
                            observation = {
                                "type": "observation",
                                "tool": "search_browser",
                                "content": "Missing 'command' parameter"
                            }

                    elif tool_name == "knowledge_manager":
                        action_type = tool_params.get("action", "")
                        if action_type == "save":
                            title = tool_params.get("title", "")
                            content = tool_params.get("content", "")
                            tags = tool_params.get("tags", [])
                            knowledge_file = f"expert_knowledge/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title[:50]}.json"
                            os.makedirs("expert_knowledge", exist_ok=True)
                            with open(knowledge_file, "w", encoding="utf-8") as f:
                                json.dump({
                                    "title": title,
                                    "content": content,
                                    "tags": tags,
                                    "created_at": datetime.now().isoformat()
                                }, f, ensure_ascii=False, indent=2)
                            observation = {
                                "type": "observation",
                                "tool": "knowledge_manager",
                                "content": f"Knowledge saved: {title}"
                            }
                        elif action_type == "retrieve":
                            query = (tool_params.get("query", "") or "").lower()
                            top_k = int(tool_params.get("top_k", 3) or 3)
                            results = []
                            if os.path.exists(EXPERT_KNOWLEDGE_DIR):
                                for filename in os.listdir(EXPERT_KNOWLEDGE_DIR):
                                    if not filename.endswith(".json"):
                                        continue
                                    file_path = os.path.join(EXPERT_KNOWLEDGE_DIR, filename)
                                    try:
                                        with open(file_path, "r", encoding="utf-8") as f:
                                            data = json.load(f)
                                        content = (data.get("content", "") or "").lower()
                                        title = (data.get("title", "") or "").lower()
                                        tags = [t.lower() for t in data.get("tags", [])]
                                        score = 0
                                        for word in query.split():
                                            if word and (word in content or word in title or word in tags):
                                                score += 1
                                        if score > 0:
                                            results.append({
                                                "title": data.get("title", ""),
                                                "content": data.get("content", ""),
                                                "tags": data.get("tags", []),
                                                "match_score": score
                                            })
                                    except Exception:
                                        continue
                            results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
                            observation = {
                                "type": "observation",
                                "tool": "knowledge_manager",
                                "content": results[:top_k]
                            }
                        else:
                            observation = {
                                "type": "observation",
                                "tool": "knowledge_manager",
                                "content": "Unsupported action. Use save or retrieve."
                            }

                    elif tool_name == "execute_tool":
                        result = tool_writer.execute_tool(
                            tool_id=tool_params.get("tool_id", ""),
                            params=tool_params.get("params", {}),
                            context=tool_params.get("context", {})
                        )
                        observation = {
                            "type": "observation",
                            "tool": "execute_tool",
                            "content": result
                        }

                    elif tool_name == "list_tools":
                        result = tool_writer.list_tools()
                        observation = {
                            "type": "observation",
                            "tool": "list_tools",
                            "content": result
                        }

                    elif tool_name == "request_human_input":
                        observation = {
                            "type": "observation",
                            "tool": "request_human_input",
                            "content": "Waiting for human input"
                        }

                    else:
                        # GENERIC FALLBACK: Try executing as a built-in or dynamic tool
                        # This avoids having to hardcode every new plugin in main.py
                        result = tool_writer.execute_tool(
                            tool_id=tool_name,
                            params=tool_params,
                            context={"task_id": task_id}
                        )
                        observation = {
                            "type": "observation",
                            "tool": tool_name,
                            "content": result
                        }
                except Exception as tool_error:
                    error_trace = traceback.format_exc()
                    observation = {
                        "type": "observation",
                        "tool": tool_name,
                        "content": {
                            "status": "error",
                            "message": str(tool_error),
                            "traceback": error_trace
                        }
                    }
            
            if observation:
                if task.steps:
                    task.steps[-1]["observation"] = observation
                
                # PERSIST: Add tool result back to history
                task.messages.append({
                    "role": "user",
                    "content": f"Observation: {json.dumps(observation, ensure_ascii=False)}"
                })
            
            if task.status == TaskStatus.WAITING_FOR_HUMAN:
                task_dict["status"] = "WAITING_HUMAN_INPUT"
                task_dict["human_input_message"] = task.human_input_pending
            
            return task_dict
            
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        raise HTTPException(status_code=500, detail=f"Task step failed: {str(e)}")

# Tool Writer APIs
class WriteToolRequest(BaseModel):
    tool_name: str
    description: str
    code: str
    parameters: dict = {}

class ExecuteToolRequest(BaseModel):
    tool_id: str
    params: dict
    context: dict = {}

class FixToolRequest(BaseModel):
    tool_id: str
    error_message: str
    new_code: str

@app.post("/tools/write")
async def write_tool(request: WriteToolRequest):
    try:
        result = tool_writer.write_tool(
            request.tool_name,
            request.description,
            request.code,
            request.parameters
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write tool: {str(e)}")

@app.post("/tools/execute")
async def execute_tool(request: ExecuteToolRequest):
    try:
        result = tool_writer.execute_tool(
            request.tool_id,
            request.params,
            request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute tool: {str(e)}")

@app.post("/tools/fix")
async def fix_tool(request: FixToolRequest):
    try:
        result = tool_writer.fix_tool(
            request.tool_id,
            request.error_message,
            request.new_code
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fix tool: {str(e)}")

@app.get("/tools/list")
async def list_tools():
    try:
        return tool_writer.list_tools()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@app.delete("/tools/{tool_id}")
async def delete_tool(tool_id: str):
    try:
        result = tool_writer.delete_tool(tool_id)
        if result["status"] == "error":
            # If not found in generated_tools, try plugins (for user-uploaded ones)
            plugin_path = os.path.join(PLUGINS_DIR, tool_id)
            if os.path.exists(plugin_path):
                # We only allow deleting non-system plugins? 
                # For simplicity, we allow deleting anything in plugins/ if requested via ID
                shutil.rmtree(plugin_path)
                return {"status": "success", "message": f"Plugin '{tool_id}' deleted"}
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {str(e)}")

@app.post("/tools/upload")
async def upload_plugin(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    try:
        content = await file.read()
        z = zipfile.ZipFile(io.BytesIO(content))
        
        # Get the name of the top-level directory in the ZIP if it exists
        top_dirs = [n.split('/')[0] for n in z.namelist() if '/' in n]
        if not top_dirs:
            # Check if index.py and manifest.json are in the root
            files = z.namelist()
            if "index.py" not in files or "manifest.json" not in files:
                raise HTTPException(status_code=400, detail="Plugin must contain index.py and manifest.json")
            
            # Use filename (without .zip) as plugin ID
            plugin_id = file.filename.replace(".zip", "")
            target_path = os.path.join(PLUGINS_DIR, plugin_id)
            os.makedirs(target_path, exist_ok=True)
            z.extractall(target_path)
        else:
            # Assume the ZIP contains exactly one directory
            plugin_id = top_dirs[0]
            target_path = os.path.join(PLUGINS_DIR, plugin_id)
            z.extractall(PLUGINS_DIR)
            
            # Validate extraction
            if not os.path.exists(os.path.join(target_path, "index.py")) or \
               not os.path.exists(os.path.join(target_path, "manifest.json")):
                shutil.rmtree(target_path)
                raise HTTPException(status_code=400, detail="Extracted plugin lacks index.py or manifest.json")
        
        return {
            "status": "success",
            "message": f"Plugin '{plugin_id}' installed successfully",
            "plugin_id": plugin_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Self-Healing & Auto-Retry APIs
class ExecuteWithRetryRequest(BaseModel):
    tool_id: str
    params: dict
    context: dict = {}
    max_retries: int = 3

@app.post("/tools/execute_with_retry")
async def execute_with_retry(request: ExecuteWithRetryRequest):
    try:
        last_error = None
        for attempt in range(request.max_retries):
            result = tool_writer.execute_tool(
                request.tool_id,
                request.params,
                request.context
            )
            
            if result["status"] == "success":
                result["attempts"] = attempt + 1
                return result
            
            last_error = result
            print(f"Attempt {attempt + 1} failed: {result.get('message')}")
            
            if attempt < request.max_retries - 1:
                import time
                time.sleep(1)
        
        if last_error:
            last_error["attempts"] = request.max_retries
            last_error["status"] = "failed"
            return last_error
        
        return {
            "status": "failed",
            "message": "All attempts failed",
            "attempts": request.max_retries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execute with retry failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
