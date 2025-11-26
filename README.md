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

- **`showTitles.py`**: Find and display all titles/sections in a PDF

- **`server_mcp.py`**: MCP server that exposes all functionality as tools

## Installation

### Prerequisites

```bash
pip install pdfplumber pymupdf PyPDF2
```

For MCP server:
```bash
pip install mcp
```

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
- `extract_embedded` (optional): Extract embedded images (default: true)
- `render_full_pages` (optional): Render full pages as images (default: true)
- `dpi` (optional): DPI for full page rendering (default: 150)

**Returns:** Image extraction summary and paths

### 5. `read_pdf_titles`
Read PDF file and extract titles/headers from the first page.

**Parameters:**
- `pdf_path` (required): Path to the PDF file

**Returns:** PDF metadata and titles

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
- `extracted/images/`: Extracted images from PDFs
- `extracted/images_extraction_result.json`: Image extraction metadata

## Notes

- Register extraction identifies registers by:
  - Font size >= 11
  - Bold text formatting
  - Contains "register" in the name
- Registers must have both address offset and reset value to be included
- Multi-page registers are supported and tracked with start/end pages

## License

[Add your license here]

