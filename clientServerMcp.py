from typing import Optional
from contextlib import AsyncExitStack
import traceback
import asyncio
import sys

# from utils.logger import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime
import logging
import json
import os

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # load environment variables from .env

# Configure logging
# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging to write to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/client.log'),  # Log to file
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

# Default system prompt for Reverse Engineering Assistant
DEFAULT_SYSTEM_PROMPT = """You are a Reverse Engineering Assistant.  

Your job is to analyze binaries, memory dumps, strings, instructions, and tool outputs.  

You explain findings clearly, step-by-step, and you highlight the most important insights.

When you receive tool results, you must return your final answer using the following JSON shape:

{
  "ok": true,
  "task_summary": "One short line describing what you found",
  "technical_findings": [],
  "recommendations": []
}

Rules:
- Write short, precise technical explanations.
- Convert any raw tool output into structured information.
- Put disassembly steps or decoded content inside "technical_findings".
- If the tool returns plain text, convert it into a readable list of observations.
- If the situation indicates an error, set "ok": false and describe the reason.
- Never change the JSON keys or their order.
- Never include extra text outside the JSON object.

Your expertise includes PE files, ELF, assembly, strings, APIs, malware behavior, unpacking, static/dynamic analysis, and memory forensics.  

Your reasoning must be correct, safe, and clear for learners."""

class MCPClient:
    def __init__(self, system_prompt: Optional[str] = None):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.llm = OpenAI(api_key=api_key)
        self.tools = []
        self.messages = []
        # Use provided system prompt, or environment variable, or default
        self.system_prompt = system_prompt or os.getenv("SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT
        self.logger = logger
        
        # Initialize with system prompt
        if self.system_prompt:
            self._ensure_system_prompt()
    
    def _ensure_system_prompt(self):
        """Ensure system prompt is always at the beginning of messages and never removed"""
        if not self.system_prompt:
            return
        # Check if system message exists at position 0
        if not self.messages or self.messages[0].get("role") != "system":
            # Remove any existing system messages (shouldn't happen, but safety)
            self.messages = [msg for msg in self.messages if msg.get("role") != "system"]
            # Insert system prompt at the beginning
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})
    
    def _limit_messages_preserving_system(self, max_messages: int):
        """Limit messages while preserving system prompt at position 0"""
        if len(self.messages) <= max_messages:
            return
        
        # Separate system message from other messages
        system_msg = None
        if self.messages and self.messages[0].get("role") == "system":
            system_msg = self.messages[0]
            other_messages = self.messages[1:]
        else:
            other_messages = self.messages
        
        # Limit other messages (keep last N-1 to make room for system message)
        if len(other_messages) > max_messages - 1:
            other_messages = other_messages[-(max_messages - 1):]
        
        # Reconstruct with system message at the beginning
        if system_msg:
            self.messages = [system_msg] + other_messages
        else:
            self.messages = other_messages
            self._ensure_system_prompt()  # Re-add system prompt if it was missing

    # connect to the MCP server
    async def connect_to_server(self, server_script_path: str):
        try:
            is_python = server_script_path.endswith(".py")
            is_js = server_script_path.endswith(".js")
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            await self.session.initialize()

            self.logger.info("Connected to MCP server")

            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]

            self.logger.info(
                f"Available tools: {[tool['name'] for tool in self.tools]}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise

    # get mcp tool list
    async def get_mcp_tools(self):
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

    # process query
    async def process_query(self, query: str):
        try:
            self.logger.info(f"Processing query: {query}")
            # Initialize messages - system prompt will be added by _ensure_system_prompt
            self.messages = []
            self._ensure_system_prompt()  # Add system prompt at position 0 (protected)
            user_message = {"role": "user", "content": query}
            self.messages.append(user_message)

            while True:
                response = await self.call_llm()

                # Extract the message from OpenAI response
                message = response.choices[0].message
                
                # the response is a text message (no tool calls)
                if not message.tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": message.content,
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    break

                # the response is a tool call
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
                self.messages.append(assistant_message)
                await self.log_conversation()

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    self.logger.info(
                        f"Calling tool {tool_name} with args {tool_args}"
                    )
                    try:
                        result = await self.session.call_tool(tool_name, tool_args)
                        self.logger.info(f"Tool {tool_name} result: {result}...")
                        
                        # Extract content from MCP result
                        # result.content is a list of TextContent objects
                        content_text = ""
                        if hasattr(result, 'content') and result.content:
                            # Extract text from each TextContent object
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
                        
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": content_text,
                            }
                        )
                        await self.log_conversation()
                    except Exception as e:
                        self.logger.error(f"Error calling tool {tool_name}: {e}")
                        raise

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    # chat loop
    async def chat_loop(self):
        while True:
            query = input("Enter your query: ")
            print(await self.process_query(query))

    # call llm
    async def call_llm(self):
        try:
            self.logger.info("Calling LLM")
            # Convert tools to OpenAI format
            openai_tools = []
            for tool in self.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }
                })
            
            # Ensure system prompt is at position 0 before sending (safety check)
            self._ensure_system_prompt()
            messages_to_send = self.messages.copy()
            
            # OpenAI client is synchronous, so we need to run it in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-4o" for more capable model
                    max_tokens=1000,
                    messages=messages_to_send,
                    tools=openai_tools if openai_tools else None,
                )
            )
            return response
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise

    # cleanup
    async def cleanup(self):
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise

    async def log_conversation(self):
        os.makedirs("conversations", exist_ok=True)

        serializable_conversation = []

        for message in self.messages:
            try:
                serializable_message = {"role": message["role"], "content": []}

                # Handle both string and list content
                if isinstance(message["content"], str):
                    serializable_message["content"] = message["content"]
                elif isinstance(message["content"], list):
                    for content_item in message["content"]:
                        if hasattr(content_item, "to_dict"):
                            serializable_message["content"].append(
                                content_item.to_dict()
                            )
                        elif hasattr(content_item, "dict"):
                            serializable_message["content"].append(content_item.dict())
                        elif hasattr(content_item, "model_dump"):
                            serializable_message["content"].append(
                                content_item.model_dump()
                            )
                        else:
                            serializable_message["content"].append(content_item)

                serializable_conversation.append(serializable_message)
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
                self.logger.debug(f"Message content: {message}")
                raise

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join("conversations", f"conversation_{timestamp}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(serializable_conversation, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing conversation to file: {str(e)}")
            self.logger.debug(f"Serializable conversation: {serializable_conversation}")
            raise
        
async def main():
    client = MCPClient()
    try:
        await client.connect_to_server(r"C:\Users\ahmed\OneDrive\Desktop\information\machine learning\projects\mcp\server_mcp.py")
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())