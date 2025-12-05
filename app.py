from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from clientServerMcp import MCPClient
import asyncio
import logging
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global MCP client instance
mcp_client: Optional[MCPClient] = None

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    reset_conversation: bool = False  # If True, starts a new conversation. If False, continues existing conversation.
    max_messages_context: Optional[int] = None  # Max messages to keep in memory for LLM (None = keep all)
    max_messages_return: Optional[int] = None  # Max messages to return in response (None = return all)

class ConnectRequest(BaseModel):
    server_script_path: str

class QueryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    success: bool

class ToolsResponse(BaseModel):
    tools: List[Dict[str, Any]]
    success: bool

class StatusResponse(BaseModel):
    connected: bool
    tools_count: int

class SystemPromptRequest(BaseModel):
    system_prompt: str

class SystemPromptResponse(BaseModel):
    system_prompt: Optional[str]
    success: bool
    message: str

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mcp_client
    # Get system prompt from environment variable (if set, otherwise uses default in MCPClient)
    system_prompt = os.getenv("SYSTEM_PROMPT", None)
    mcp_client = MCPClient(system_prompt=system_prompt)
    logger.info("MCP Client initialized")
    if system_prompt:
        logger.info("System prompt loaded from environment")
    else:
        logger.info("Using default Reverse Engineering Assistant system prompt")
    yield
    # Shutdown
    if mcp_client:
        try:
            await mcp_client.cleanup()
            logger.info("MCP Client cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create FastAPI app
app = FastAPI(
    title="MCP Client API",
    description="API for interacting with MCP (Model Context Protocol) server",
    version="1.0.0",
    lifespan=lifespan
)

# Dependency to get MCP client
async def get_client() -> MCPClient:
    if mcp_client is None:
        raise HTTPException(status_code=503, detail="MCP Client not initialized")
    return mcp_client

# Routes
@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "MCP Client API is running",
        "status": "healthy"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "client_initialized": mcp_client is not None
    }

@app.post("/connect", response_model=ToolsResponse)
async def connect_to_server(request: ConnectRequest, client: MCPClient = Depends(get_client)):
    """Connect to an MCP server"""
    try:
        if not os.path.exists(request.server_script_path):
            raise HTTPException(
                status_code=404,
                detail=f"Server script not found: {request.server_script_path}"
            )
        
        await client.connect_to_server(request.server_script_path)
        tools = await client.get_mcp_tools()
        
        tools_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]
        
        return ToolsResponse(tools=tools_list, success=True)
    except Exception as e:
        logger.error(f"Error connecting to server: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, client: MCPClient = Depends(get_client)):
    """
    Process a query using the MCP client.
    
    - reset_conversation: If True, starts fresh. If False, continues conversation.
    - max_messages_context: Max messages to keep in memory for LLM (None = keep all)
    - max_messages_return: Max messages to return in response (None = return all)
    """
    try:
        if not client.session:
            raise HTTPException(
                status_code=400,
                detail="Not connected to MCP server. Please connect first using /connect"
            )
        
        # If resetting conversation, use process_query which resets messages
        if request.reset_conversation:
            messages = await client.process_query(request.query)
            # Limit messages to return (just for response)
            if request.max_messages_return and len(messages) > request.max_messages_return:
                messages = messages[-request.max_messages_return:]
        else:
            # Continue conversation: add user message to existing messages
            # Ensure system prompt is always at the beginning (protected)
            client._ensure_system_prompt()
            user_message = {"role": "user", "content": request.query}
            client.messages.append(user_message)
            
            # Limit messages in memory (sliding window) to avoid token limit issues
            # System prompt is protected and always stays at position 0
            if request.max_messages_context:
                client._limit_messages_preserving_system(request.max_messages_context)
            
            # Process the query with existing conversation history
            # We need to manually handle the LLM call and tool execution
            while True:
                response = await client.call_llm()
                message = response.choices[0].message
                
                # If response is text only (no tool calls)
                if not message.tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content,
                    }
                    client.messages.append(assistant_message)
                    await client.log_conversation()
                    break
                
                # If response has tool calls
                assistant_message = {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            }
                        }
                        for tool_call in message.tool_calls
                    ],
                }
                client.messages.append(assistant_message)
                await client.log_conversation()
                
                # Execute tool calls
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    logger.info(f"Calling tool {tool_name} with args {tool_args}")
                    
                    try:
                        result = await client.session.call_tool(tool_name, tool_args)
                        logger.info(f"Tool {tool_name} result: {result}...")
                        
                        # Extract content from MCP result
                        content_text = ""
                        if hasattr(result, 'content') and result.content:
                            content_parts = []
                            for content_item in result.content:
                                if hasattr(content_item, 'text'):
                                    content_parts.append(content_item.text)
                                elif isinstance(content_item, str):
                                    content_parts.append(content_item)
                                else:
                                    content_parts.append(str(content_item))
                            content_text = "\n".join(content_parts) if content_parts else ""
                        else:
                            content_text = str(result)
                        
                        client.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": content_text,
                        })
                        await client.log_conversation()
                    except Exception as e:
                        logger.error(f"Error calling tool {tool_name}: {e}")
                        raise
            
            messages = client.messages
        
        # Limit messages to return (just for response, doesn't affect stored messages)
        if request.max_messages_return and len(messages) > request.max_messages_return:
            messages = messages[-request.max_messages_return:]
        
        # Convert messages to serializable format
        serializable_messages = []
        for msg in messages:
            serializable_msg = {
                "role": msg.get("role"),
                "content": msg.get("content", ""),
            }
            if "tool_calls" in msg:
                serializable_msg["tool_calls"] = msg["tool_calls"]
            serializable_messages.append(serializable_msg)
        
        return QueryResponse(messages=serializable_messages, success=True)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools", response_model=ToolsResponse)
async def get_tools(client: MCPClient = Depends(get_client)):
    """Get available MCP tools"""
    try:
        if not client.session:
            raise HTTPException(
                status_code=400,
                detail="Not connected to MCP server. Please connect first using /connect"
            )
        
        tools = await client.get_mcp_tools()
        tools_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]
        
        return ToolsResponse(tools=tools_list, success=True)
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def get_status(client: MCPClient = Depends(get_client)):
    """Get current connection status"""
    try:
        connected = client.session is not None
        tools_count = len(client.tools) if client.tools else 0
        return StatusResponse(connected=connected, tools_count=tools_count)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/clear")
async def clear_conversation(client: MCPClient = Depends(get_client)):
    """Clear the conversation history (like restarting chat_loop)"""
    try:
        client.messages = []
        # Re-add system prompt after clearing (it's protected)
        client._ensure_system_prompt()
        logger.info("Conversation history cleared")
        return {"success": True, "message": "Conversation history cleared"}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/history", response_model=QueryResponse)
async def get_conversation_history(client: MCPClient = Depends(get_client)):
    """Get the current conversation history"""
    try:
        # Convert messages to serializable format
        serializable_messages = []
        for msg in client.messages:
            serializable_msg = {
                "role": msg.get("role"),
                "content": msg.get("content", ""),
            }
            if "tool_calls" in msg:
                serializable_msg["tool_calls"] = msg["tool_calls"]
            serializable_messages.append(serializable_msg)
        
        return QueryResponse(messages=serializable_messages, success=True)
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(client: MCPClient = Depends(get_client)):
    """
    Get the current system prompt.
    
    **Response:**
    ```json
    {
      "system_prompt": "Your system prompt here",
      "success": true,
      "message": "System prompt retrieved"
    }
    ```
    """
    try:
        return SystemPromptResponse(
            system_prompt=client.system_prompt,
            success=True,
            message="System prompt retrieved"
        )
    except Exception as e:
        logger.error(f"Error getting system prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system-prompt", response_model=SystemPromptResponse)
async def set_system_prompt(request: SystemPromptRequest, client: MCPClient = Depends(get_client)):
    """
    Set, update, or remove the system prompt.
    
    **Set/Update:**
    ```json
    {
      "system_prompt": "You are a helpful assistant. Always format responses as JSON."
    }
    ```
    
    **Remove (set to empty string):**
    ```json
    {
      "system_prompt": ""
    }
    ```
    
    **Response:**
    ```json
    {
      "system_prompt": "You are a helpful assistant...",
      "success": true,
      "message": "System prompt updated successfully"
    }
    ```
    """
    try:
        # Update or remove system prompt
        if request.system_prompt.strip():
            # Set/update system prompt
            client.system_prompt = request.system_prompt
            # Update system message in existing messages if conversation has started
            if client.messages:
                client._ensure_system_prompt()
            else:
                client._ensure_system_prompt()
            logger.info("System prompt updated")
            message = "System prompt updated successfully"
        else:
            # Remove system prompt (empty string)
            client.system_prompt = None
            # Remove system message from messages if it exists
            if client.messages and client.messages[0].get("role") == "system":
                client.messages = client.messages[1:]
            logger.info("System prompt removed")
            message = "System prompt removed successfully"
        
        return SystemPromptResponse(
            system_prompt=client.system_prompt,
            success=True,
            message=message
        )
    except Exception as e:
        logger.error(f"Error setting system prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1",port=8000)
