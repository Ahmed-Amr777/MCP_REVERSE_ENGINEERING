import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
import os
import json
from pathlib import Path
from extractRawRegisters import extract_raw_registers
from searchRegister import search_register
from pdfReturnImages import extract_images_from_pages, extract_page_as_image
from pdfInfo import get_pdf_titles
from pdfReturnCuted import extract_pdf_pages

app = Server("my-custom-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="extract_registers",
            description="Extract all registers from a PDF file. Returns registers with start_page, end_page, address_offset, reset_value, and content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the PDF file"},
                    "output_dir": {"type": "string", "description": "Output directory for JSON and TXT files (default: extracted)"}
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="search_register",
            description="Search for registers by name (full name, short name, or partial match). Returns matching registers with all fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "register_name": {"type": "string", "description": "Register name to search for"},
                    "json_path": {"type": "string", "description": "Path to registers JSON file (default: extracted/registers.json)"}
                },
                "required": ["register_name"]
            }
        ),
        Tool(
            name="extract_pdf_images",
            description="Extract images from PDF pages. Extracts embedded images and/or renders full pages as images. Returns JSON with image paths and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the PDF file"},
                    "start_page": {"type": "integer", "description": "Starting page number (1-indexed)"},
                    "end_page": {"type": "integer", "description": "Ending page number (1-indexed)"},
                    "output_dir": {"type": "string", "description": "Output directory for images (default: extracted)"},
                    "extract_embedded": {"type": "boolean", "description": "Extract embedded images from PDF"},
                    "render_full_pages": {"type": "boolean", "description": "Render full pages as PNG images"},
                    "dpi": {"type": "integer", "description": "DPI resolution for full page rendering"}
                },
                "required": ["pdf_path", "start_page", "end_page", "extract_embedded", "render_full_pages", "dpi"]
            }
        ),
        Tool(
            name="get_pdf_titles",
            description="Get PDF titles (table of contents) in a range and basic PDF information. Returns simple structure with title names and page numbers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the PDF file"},
                    "start_title": {"type": "integer", "description": "Starting title number (1-indexed, default: 1)"},
                    "end_title": {"type": "integer", "description": "Ending title number (1-indexed, default: None = all titles)"}
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="extract_pdf_pages",
            description="Extract a range of pages from a PDF and save as a new PDF file. Returns the path to the extracted PDF and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the source PDF file"},
                    "start_page": {"type": "integer", "description": "Starting page number (1-indexed)"},
                    "end_page": {"type": "integer", "description": "Ending page number (1-indexed, inclusive)"},
                    "output_path": {"type": "string", "description": "Path for the output PDF file. If not provided, auto-generates in extracted/ folder."}
                },
                "required": ["pdf_path", "start_page", "end_page"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "extract_registers":
        pdf_path = arguments.get("pdf_path", "")
        output_dir = arguments.get("output_dir", "extracted")  # Default to "extracted"
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            # Resolve output_dir to absolute path to ensure consistency
            if isinstance(output_dir, str):
                output_dir = Path(output_dir)
            output_dir = output_dir.resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract registers
            registers = extract_raw_registers(pdf_path)
            
            # Save to JSON
            json_file = output_dir / "registers.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(registers, f, indent=2, ensure_ascii=False)
            
            # Save to TXT
            txt_file = output_dir / "registers_all.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                for r in registers:
                    if r['section']:
                        f.write(f"{r['section']} ")
                    f.write(f"{r['full_name']}\n\n")
                    f.write(f"Address offset: {r['address_offset']}\n")
                    f.write(f"Reset value: {r['reset_value']}\n\n")
                    if r['content']:
                        f.write(r['content'])
                        f.write("\n")
                    f.write("\n" + "="*70 + "\n\n")
            
            result = f"Extracted {len(registers)} registers from PDF.\n"
            result += f"JSON saved to: {json_file}\n"
            result += f"TXT saved to: {txt_file}\n"
            
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting registers: {str(e)}")]
    
    elif name == "search_register":
        register_name = arguments.get("register_name", "")
        json_path = arguments.get("json_path", "extracted/registers.json")  # Default to "extracted/registers.json"
        
        if not register_name:
            return [TextContent(type="text", text="Error: register_name is required")]
        
        try:
            # Resolve json_path to absolute path if it's a relative path
            if json_path and not os.path.isabs(json_path):
                json_path = str(Path(json_path).resolve())
            
            results = search_register(register_name, json_path)
            
            if not results:
                return [TextContent(type="text", text=f"No registers found matching '{register_name}'")]
            
            result_text = f"Found {len(results)} matching register(s):\n\n"
            for i, reg in enumerate(results, 1):
                result_text += f"Match {i}:\n"
                result_text += json.dumps(reg, indent=2, ensure_ascii=False)
                result_text += "\n\n" + "="*70 + "\n\n"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching registers: {str(e)}")]
    
    elif name == "extract_pdf_images":
        pdf_path = arguments.get("pdf_path", "")
        start_page = arguments.get("start_page")
        end_page = arguments.get("end_page")
        output_dir = arguments.get("output_dir", "extracted")  # Default to "extracted"
        extract_embedded = arguments.get("extract_embedded")
        render_full_pages = arguments.get("render_full_pages")
        dpi = arguments.get("dpi")
        
        # Validate required parameters
        if not pdf_path:
            return [TextContent(type="text", text="Error: pdf_path is required")]
        if start_page is None or end_page is None:
            return [TextContent(type="text", text="Error: start_page and end_page are required")]
        if extract_embedded is None or render_full_pages is None:
            return [TextContent(type="text", text="Error: extract_embedded and render_full_pages are required")]
        if dpi is None:
            return [TextContent(type="text", text="Error: dpi is required")]
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            # Resolve output_dir to absolute path to ensure consistency
            if isinstance(output_dir, str):
                output_dir = Path(output_dir)
            output_dir = output_dir.resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result_data = {
                "pdf_path": pdf_path,
                "pages_range": {"start": start_page, "end": end_page},
                "output_dir": str(output_dir),
                "output_dir_absolute": str(output_dir.absolute())
            }
            
            # Extract embedded images
            if extract_embedded:
                images_result = extract_images_from_pages(pdf_path, start_page, end_page, output_dir)
                result_data["embedded_images"] = images_result
            else:
                result_data["embedded_images"] = {"pages": [], "total_images": 0}
            
            # Render full pages
            if render_full_pages:
                full_page_images = []
                for page_num in range(start_page, end_page + 1):
                    try:
                        page_image_path = extract_page_as_image(pdf_path, page_num, output_dir, dpi)
                        # Verify image was created - ensure we use absolute path
                        img_path = Path(page_image_path)
                        if not img_path.is_absolute():
                            img_path = img_path.resolve()
                        if not img_path.exists():
                            raise FileNotFoundError(f"Image file not found at {img_path}")
                        # Always use absolute path - ensure it's really absolute
                        absolute_img_path = img_path.absolute()
                        # Verify it exists
                        if not absolute_img_path.exists():
                            raise FileNotFoundError(f"Image file not found at {absolute_img_path}")
                        
                        full_page_images.append({
                            "page_number": page_num,
                            "image_path": str(absolute_img_path),
                            "file_exists": absolute_img_path.exists(),
                            "file_size": absolute_img_path.stat().st_size if absolute_img_path.exists() else 0
                        })
                    except Exception as e:
                        # Log error but continue with other pages
                        full_page_images.append({
                            "page_number": page_num,
                            "error": str(e),
                            "image_path": None
                        })
                result_data["full_page_images"] = full_page_images
            else:
                result_data["full_page_images"] = []
            
            # Add summary
            result_data["summary"] = {
                "total_embedded_images": result_data["embedded_images"]["total_images"],
                "total_full_page_images": len(result_data["full_page_images"]),
                "pages_with_images": len(result_data["embedded_images"]["pages"]),
                "status": "success"
            }
            
            # Return JSON directly for MCP - use compact format for better MCP compatibility
            result_json = json.dumps(result_data, ensure_ascii=False)
            return [TextContent(type="text", text=result_json)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting images: {str(e)}")]
    
    elif name == "get_pdf_titles":
        pdf_path = arguments.get("pdf_path", "")
        start_title = arguments.get("start_title", 1)
        end_title = arguments.get("end_title", None)
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            result = get_pdf_titles(pdf_path, start_title, end_title)
            # Return JSON directly as string
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting PDF titles: {str(e)}")]
    
    elif name == "extract_pdf_pages":
        pdf_path = arguments.get("pdf_path", "")
        start_page = arguments.get("start_page")
        end_page = arguments.get("end_page")
        output_path = arguments.get("output_path", None)
        
        # Validate required parameters
        if not pdf_path:
            return [TextContent(type="text", text="Error: pdf_path is required")]
        if start_page is None or end_page is None:
            return [TextContent(type="text", text="Error: start_page and end_page are required")]
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            result = extract_pdf_pages(pdf_path, start_page, end_page, output_path)
            # Return JSON directly as string
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting PDF pages: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())

