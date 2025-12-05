# STM32 Register Extraction and MCP Server

This project provides tools for extracting register information from STM32 PDF documentation and accessing it through an MCP (Model Context Protocol) server.

## Features

- **Register Extraction**: Extract all registers from STM32 PDF documentation with page ranges, addresses, reset values, and content
- **Register Search**: Search for registers by name (full name, short name, or partial match)
- **PDF Image Extraction**: Extract embedded images or render full pages as images from PDFs
- **MCP Server**: Access all functionality through a Model Context Protocol server

## Project Structure

### Main Scripts

- **`extractRawRegisters.py`**: Extracts all registers from a PDF file
  - Identifies registers by font size (>=11) and bold formatting
  - Extracts: section, full name, short name, address offset, reset value, start/end pages, and content
  - Outputs: `registers.json` and `registers_all.txt`

- **`searchRegister.py`**: Search for registers by name
  - Functions: `search_register()` and `get_register_by_name()`
  - Searches in the extracted registers JSON file

- **`pdfReturnImages.py`**: Extract images from PDF pages
  - Extract embedded images from PDF pages
  - Render full pages as images
  - Supports custom DPI settings

- **`pdfInfo.py`**: Extract PDF titles (table of contents) and basic PDF information

- **`server_mcp.py`**: MCP server that exposes all functionality as tools

- **`clientServerMcp.py`**: MCP client that connects to the MCP server and uses OpenAI to process queries with function calling

- **`app.py`**: FastAPI web server that provides REST API endpoints for interacting with the MCP client

## Installation and Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager) or uv (recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Ahmed-Amr777/MCP_REVERSE_ENGINEERING.git
cd MCP_REVERSE_ENGINEERING
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

**Using pip:**
```bash
pip install -r requirements.txt
```

**Using uv (recommended):**
```bash
uv pip install -r requirements.txt
```

**Required Dependencies:**
- `pdfplumber` - PDF text and character extraction
- `pymupdf` (PyMuPDF) - PDF image extraction, rendering, and table of contents
- `mcp` - Model Context Protocol server framework
- `openai` - OpenAI API client for LLM integration
- `python-dotenv` - Environment variable management
- `fastapi` - Web framework for building APIs
- `uvicorn` - ASGI server for running FastAPI
- `google-generativeai` - Google Gemini API client (optional, for testing)

**Note:** Do NOT install the `fitz` package separately. Use `pymupdf` and import it as `import pymupdf as fitz` to avoid conflicts.

### Step 4: Create Output Directory

The scripts will automatically create the `extracted/` directory, but you can create it manually:

```bash
mkdir extracted
```

### Step 5: Set Up Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# .env file
OPENAI_API_KEY=your_openai_api_key_here
# Optional: For testing Gemini
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: Custom system prompt (defaults to Reverse Engineering Assistant)
SYSTEM_PROMPT=Your custom system prompt here
```

**Note:** 
- The MCP client requires `OPENAI_API_KEY` to be set. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys).
- If `SYSTEM_PROMPT` is not set, the default Reverse Engineering Assistant prompt will be used.
- The `.env` file is ignored by git (see `.gitignore`).

### Step 6: Configure MCP Server

Add the MCP server to your MCP client configuration. Example for Cursor/Claude Desktop:

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["path/to/server_mcp.py"]
    }
  }
}
```

Or if using a virtual environment:

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "path/to/.venv/Scripts/python.exe",
      "args": ["path/to/server_mcp.py"]
    }
  }
}
```

### Step 7: Verify Installation

Test the installation by running a simple script:

```bash
python searchRegister.py
```

Or test the MCP server:

```bash
python server_mcp.py
```

### Troubleshooting

**If you encounter import errors:**
- Make sure your virtual environment is activated
- Verify all dependencies are installed: `pip list` or `uv pip list`
- Try reinstalling: `pip install --upgrade -r requirements.txt`

**If you get `ModuleNotFoundError: No module named 'frontend'`:**
- This happens if the wrong `fitz` package is installed
- Solution: The code already uses `import pymupdf as fitz` (fixed)
- If you have the conflicting `fitz` package installed, remove it:
  ```bash
  uv pip uninstall fitz
  # or
  pip uninstall fitz
  ```
- Do NOT install the `fitz` package separately - use `pymupdf` instead

**If PDF processing fails:**
- Ensure the PDF file path is correct
- Check that the PDF is not corrupted
- Verify you have read permissions for the PDF file

**If MCP server crashes on startup:**
- Make sure you're using Python 3.10 or higher
- Verify all dependencies are installed in the correct environment
- Check that the server script path in MCP config is correct

**If MCP client fails with API key error:**
- Ensure `OPENAI_API_KEY` is set in your `.env` file
- Verify the API key is valid and has credits/quota
- Check that `python-dotenv` is installed: `pip install python-dotenv`

**If tool calling fails:**
- Verify the MCP server is running correctly
- Check that tool names match between server and client
- Review `logs/client.log` for detailed error messages

## Usage

### Extract Registers from PDF

```python
from extractRawRegisters import extract_raw_registers

pdf_path = "path/to/stm32f10xxx.pdf"
registers = extract_raw_registers(pdf_path)

# Registers are saved to:
# - extracted/registers.json
# - extracted/registers_all.txt
```

Or run directly:
```bash
python extractRawRegisters.py
```

### Search for Registers

```python
from searchRegister import search_register, get_register_by_name

# Search for all matching registers
results = search_register("CRC_DR")

# Get a single register by exact name
register = get_register_by_name("CRC_DR")
```

Or run directly:
```bash
python searchRegister.py
```

### Extract PDF Images

```python
from pdfReturnImages import extract_images_from_pages, extract_page_as_image

# Extract embedded images from pages 122-125
result = extract_images_from_pages("path/to/pdf", 122, 125, Path("extracted"))

# Render full page as image
image_path = extract_page_as_image("path/to/pdf", 122, Path("extracted"), dpi=150)
```

Or run directly:
```bash
python pdfReturnImages.py
```

## MCP Server Tools

The MCP server provides the following tools:

### 1. `extract_registers`
Extract all registers from a PDF file.

**Parameters:**
- `pdf_path` (required): Path to the PDF file
- `output_dir` (optional): Output directory (default: "extracted")

**Returns:** Number of registers extracted and file paths

### 2. `search_register`
Search for registers by name (supports partial matching).

**Parameters:**
- `register_name` (required): Register name to search for
- `json_path` (optional): Path to registers JSON file (default: "extracted/registers.json")

**Returns:** List of matching registers with complete data

### 3. `get_register`
Get a single register by exact name match.

**Parameters:**
- `register_name` (required): Register name to get
- `json_path` (optional): Path to registers JSON file (default: "extracted/registers.json")

**Returns:** Complete register data

### 4. `extract_pdf_images`
Extract images from PDF pages.

**Parameters:**
- `pdf_path` (required): Path to the PDF file
- `start_page` (required): Starting page number (1-indexed)
- `end_page` (required): Ending page number (1-indexed)
- `output_dir` (optional): Output directory (default: "extracted")
- `extract_embedded` (required): Extract embedded images (true/false)
- `render_full_pages` (required): Render full pages as images (true/false)
- `dpi` (required): DPI resolution for full page rendering

**Returns:** JSON with image paths and metadata

### 5. `get_pdf_titles`
Get PDF titles (table of contents) and basic PDF information.

**Parameters:**
- `pdf_path` (required): Path to the PDF file
- `start_title` (optional): Starting title number (1-indexed, default: 1)
- `end_title` (optional): Ending title number (1-indexed, default: 10, or None for all)

**Returns:** PDF info (total pages, title) and list of titles with page numbers

## Running the MCP Server

```bash
python server_mcp.py
```

The server will run on stdio and can be connected to via MCP clients.

## MCP Client with OpenAI

The `clientServerMcp.py` script provides an interactive client that:
- Connects to the MCP server
- Uses OpenAI's GPT models (default: `gpt-4o-mini`) with function calling
- Processes natural language queries and automatically calls MCP tools
- Maintains conversation history and logs

### Running the MCP Client

```bash
python clientServerMcp.py <path_to_server_script>
```

**Example:**
```bash
python clientServerMcp.py server_mcp.py
```

Or with virtual environment:
```bash
.venv\Scripts\python.exe clientServerMcp.py server_mcp.py
```

### How It Works

1. **Connection**: The client connects to the MCP server via stdio
2. **Tool Discovery**: Automatically discovers all available tools from the MCP server
3. **Query Processing**: 
   - Sends user queries to OpenAI with available tools
   - OpenAI decides which tools to call based on the query
   - Executes tool calls through the MCP server
   - Returns results back to OpenAI for final response
4. **Logging**: All conversations are logged to:
   - `logs/client.log` - Detailed execution logs
   - `conversations/conversation_YYYY-MM-DD_HH-MM-SS.json` - Conversation history

### Example Usage

Once running, you can interact with the client:

```
Enter your query: Extract all registers from "C:\path\to\stm32f10xxx.pdf"
Enter your query: Search for CRC_DR register
Enter your query: Get page 4 from the PDF as an image
```

### Configuration

You can modify the OpenAI model in `clientServerMcp.py`:

```python
model="gpt-4o-mini"  # Change to "gpt-4o", "gpt-4-turbo", etc.
```

### Features

- **Automatic Tool Calling**: OpenAI automatically determines which MCP tools to use
- **Multi-turn Conversations**: Maintains context across multiple queries
- **Error Handling**: Graceful error handling with detailed logging
- **Conversation Logging**: All conversations saved as JSON files

## Register Data Structure

Each register in the JSON file contains:

```json
{
  "start_page": 51,
  "end_page": 52,
  "page_range": "51-52",
  "section": "3.4.1",
  "full_name": "Data register (CRC_DR)",
  "short_name": "CRC_DR",
  "address_offset": "0x00",
  "reset_value": "0xFFFF FFFF",
  "content": "Register content text..."
}
```

## Output Files

- `extracted/registers.json`: All registers in JSON format
- `extracted/registers_all.txt`: All registers in human-readable text format
- `extracted/`: Extracted images from PDFs (saved directly here, no subfolder)

## Notes

- Register extraction identifies registers by:
  - Font size >= 11 or 12
  - Bold text formatting
  - Contains "register" in the name
- Registers must have both address offset and reset value to be included
- Multi-page registers are supported and tracked with start/end pages
- Content filtering removes single-character lines, short numbers, and repetitive patterns
- All output directories are optional and default to `"extracted"` if not specified

## FastAPI REST API

The `app.py` file provides a REST API for interacting with the MCP client through HTTP requests.

### Starting the API Server

```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`

### API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: `http://127.0.0.1:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://127.0.0.1:8000/redoc` (ReDoc)

### API Endpoints

#### 1. `GET /` - Health Check
Root endpoint that returns API status.

**Response:**
```json
{
  "message": "MCP Client API is running",
  "status": "healthy"
}
```

#### 2. `GET /health` - Health Check
Returns detailed health status.

**Response:**
```json
{
  "status": "healthy",
  "client_initialized": true
}
```

#### 3. `POST /connect` - Connect to MCP Server
Connects to an MCP server and retrieves available tools.

**Request Body:**
```json
{
  "server_script_path": "C:\\path\\to\\server_mcp.py"
}
```

**Response:**
```json
{
  "tools": [
    {
      "name": "search_register",
      "description": "Search for registers by name",
      "input_schema": {
        "type": "object",
        "properties": {
          "register_name": {"type": "string"}
        }
      }
    }
  ],
  "success": true
}
```

**Errors:**
- `404`: Server script file not found
- `500`: Connection error

#### 4. `POST /query` - Process Query
Main endpoint for sending queries to the AI. Processes your query, uses MCP tools if needed, and returns the conversation.

**Request Body:**
```json
{
  "query": "What is Python?",
  "reset_conversation": false,
  "max_messages_context": 10,
  "max_messages_return": 3
}
```

**Parameters:**
- `query` (required): Your question or request
- `reset_conversation` (optional, default: `false`): If `true`, starts a fresh conversation. If `false`, continues existing conversation.
- `max_messages_context` (optional): Maximum messages to keep in memory for LLM (sliding window). `null` = keep all. Helps avoid token limits.
- `max_messages_return` (optional): Maximum messages to return in response JSON. `null` = return all. Only affects response size, not stored messages.

**Response:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is Python?"
    },
    {
      "role": "assistant",
      "content": "Python is a programming language..."
    }
  ],
  "success": true
}
```

**Example - Continue Conversation:**
```json
// First request
POST /query
{
  "query": "What is Python?"
}

// Second request (continues conversation)
POST /query
{
  "query": "Tell me more",
  "reset_conversation": false
}
```

**Example - Limit Response:**
```json
// Get only last 2 messages in response
POST /query
{
  "query": "Hello",
  "max_messages_return": 2
}
```

**Errors:**
- `400`: Not connected to MCP server
- `500`: Processing error

#### 5. `GET /tools` - Get Available Tools
Returns a list of all tools available from the connected MCP server.

**Response:**
```json
{
  "tools": [
    {
      "name": "search_register",
      "description": "Search for registers by name",
      "input_schema": {...}
    }
  ],
  "success": true
}
```

**Errors:**
- `400`: Not connected to MCP server

#### 6. `GET /status` - Get Connection Status
Returns whether the client is connected to an MCP server and how many tools are available.

**Response:**
```json
{
  "connected": true,
  "tools_count": 5
}
```

#### 7. `POST /conversation/clear` - Clear Conversation History
Removes all messages from the conversation, effectively starting fresh.

**Response:**
```json
{
  "success": true,
  "message": "Conversation history cleared"
}
```

#### 8. `GET /conversation/history` - Get Conversation History
Returns all messages in the current conversation.

**Response:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is Python?"
    },
    {
      "role": "assistant",
      "content": "Python is a programming language..."
    }
  ],
  "success": true
}
```

#### 9. `GET /system-prompt` - Get Current System Prompt
Returns the current system prompt being used.

**Response:**
```json
{
  "system_prompt": "You are a Reverse Engineering Assistant...",
  "success": true,
  "message": "System prompt retrieved"
}
```

#### 10. `POST /system-prompt` - Set, Update, or Remove System Prompt
Sets, updates, or removes the system prompt.

**Set/Update:**
```json
{
  "system_prompt": "You are a helpful assistant. Always format responses as JSON."
}
```

**Remove (send empty string):**
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

### Default System Prompt

The API comes with a default **Reverse Engineering Assistant** system prompt that formats responses as structured JSON:

```json
{
  "ok": true,
  "task_summary": "One short line describing what you found",
  "technical_findings": [],
  "recommendations": []
}
```

The system prompt is:
- **Protected**: Always at position 0, never removed
- **Automatic**: Applied to all conversations by default
- **Customizable**: Can be changed via `POST /system-prompt` or `SYSTEM_PROMPT` environment variable

### Example Usage with curl

```bash
# 1. Connect to server
curl -X POST "http://127.0.0.1:8000/connect" \
  -H "Content-Type: application/json" \
  -d '{"server_script_path": "server_mcp.py"}'

# 2. Send a query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Search for CRC_DR register"}'

# 3. Continue conversation
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me more about it", "max_messages_return": 2}'

# 4. Get status
curl -X GET "http://127.0.0.1:8000/status"

# 5. Clear conversation
curl -X POST "http://127.0.0.1:8000/conversation/clear"

# 6. Get system prompt
curl -X GET "http://127.0.0.1:8000/system-prompt"

# 7. Update system prompt
curl -X POST "http://127.0.0.1:8000/system-prompt" \
  -H "Content-Type: application/json" \
  -d '{"system_prompt": "Your custom prompt here"}'
```

### Message Limits Explained

- **`max_messages_context`**: Limits how many messages are sent to the LLM. This saves tokens and helps avoid hitting token limits. Uses a sliding window (keeps only the last N messages).

- **`max_messages_return`**: Limits how many messages appear in the JSON response. This only affects what you see in the response, not what's stored in memory or sent to the LLM.

**Example:**
```json
{
  "query": "Hello",
  "max_messages_context": 10,  // Only last 10 messages sent to LLM
  "max_messages_return": 3      // Only last 3 messages in response
}
```

### API Workflow

1. **Start the server**: `python app.py`
2. **Connect to MCP server**: `POST /connect` with server path
3. **Optional - Set system prompt**: `POST /system-prompt` to customize (or use default)
4. **Send queries**: `POST /query` with your questions
5. **Continue conversation**: Send more queries without resetting
6. **Manage conversation**: Use `/conversation/clear` or `/conversation/history` as needed

## License

[Add your license here]

