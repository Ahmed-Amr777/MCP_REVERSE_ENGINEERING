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

**Note:** Do NOT install the `fitz` package separately. Use `pymupdf` and import it as `import pymupdf as fitz` to avoid conflicts.

### Step 4: Create Output Directory

The scripts will automatically create the `extracted/` directory, but you can create it manually:

```bash
mkdir extracted
```

### Step 5: Configure MCP Server

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

### Step 6: Verify Installation

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

## License

[Add your license here]

