import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
import PyPDF2
import os
import json
from pathlib import Path
from extractRawRegisters import extract_raw_registers
from searchRegister import search_register, get_register_by_name
from pdfReturnImages import extract_images_from_pages, extract_page_as_image

app = Server("my-custom-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="read_pdf_titles",
            description="Reads PDF file and extracts titles/headers from the first page",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the PDF file"}
                },
                "required": ["pdf_path"]
            }
        ),
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
            name="get_register",
            description="Get a single register by exact name match. Returns the complete register data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "register_name": {"type": "string", "description": "Register name to get"},
                    "json_path": {"type": "string", "description": "Path to registers JSON file (default: extracted/registers.json)"}
                },
                "required": ["register_name"]
            }
        ),
        Tool(
            name="extract_pdf_images",
            description="Extract images from PDF pages. Can extract embedded images or render full pages as images.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string", "description": "Path to the PDF file"},
                    "start_page": {"type": "integer", "description": "Starting page number (1-indexed)"},
                    "end_page": {"type": "integer", "description": "Ending page number (1-indexed)"},
                    "output_dir": {"type": "string", "description": "Output directory (default: extracted)"},
                    "extract_embedded": {"type": "boolean", "description": "Extract embedded images (default: true)"},
                    "render_full_pages": {"type": "boolean", "description": "Render full pages as images (default: true)"},
                    "dpi": {"type": "integer", "description": "DPI for full page rendering (default: 150)"}
                },
                "required": ["pdf_path", "start_page", "end_page"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "read_pdf_titles":
        pdf_path = arguments.get("pdf_path", "")
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: File not found at {pdf_path}")]
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                # Extract text from first page
                first_page = reader.pages[0]
                text = first_page.extract_text()
                lines = text.split('\n')
                titles = [line.strip() for line in lines if line.strip()]
                
                result = f"PDF: {os.path.basename(pdf_path)}\n"
                result += f"Total Pages: {num_pages}\n"
                result += f"Number of Headers/Titles: {len(titles)}\n\n"
                result += "Headers/Titles:\n" + "\n".join(titles[:10])  # First 10 titles
                
                return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading PDF: {str(e)}")]
    
    elif name == "extract_registers":
        pdf_path = arguments.get("pdf_path", "")
        output_dir = Path(arguments.get("output_dir", "extracted"))
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            output_dir.mkdir(exist_ok=True)
            
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
        json_path = arguments.get("json_path", "extracted/registers.json")
        
        if not register_name:
            return [TextContent(type="text", text="Error: register_name is required")]
        
        try:
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
    
    elif name == "get_register":
        register_name = arguments.get("register_name", "")
        json_path = arguments.get("json_path", "extracted/registers.json")
        
        if not register_name:
            return [TextContent(type="text", text="Error: register_name is required")]
        
        try:
            register = get_register_by_name(register_name, json_path)
            
            if not register:
                return [TextContent(type="text", text=f"Register '{register_name}' not found")]
            
            result_text = json.dumps(register, indent=2, ensure_ascii=False)
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting register: {str(e)}")]
    
    elif name == "extract_pdf_images":
        pdf_path = arguments.get("pdf_path", "")
        start_page = arguments.get("start_page", 1)
        end_page = arguments.get("end_page", 1)
        output_dir = Path(arguments.get("output_dir", "extracted"))
        extract_embedded = arguments.get("extract_embedded", True)
        render_full_pages = arguments.get("render_full_pages", True)
        dpi = arguments.get("dpi", 150)
        
        if not os.path.exists(pdf_path):
            return [TextContent(type="text", text=f"Error: PDF file not found at {pdf_path}")]
        
        try:
            output_dir.mkdir(exist_ok=True)
            result_data = {
                "pdf_path": pdf_path,
                "pages_range": {"start": start_page, "end": end_page}
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
                    page_image_path = extract_page_as_image(pdf_path, page_num, output_dir, dpi)
                    full_page_images.append({
                        "page_number": page_num,
                        "image_path": page_image_path
                    })
                result_data["full_page_images"] = full_page_images
            else:
                result_data["full_page_images"] = []
            
            # Save results
            output_file = output_dir / "images_extraction_result.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            result_text = f"Extracted images from pages {start_page} to {end_page}.\n"
            result_text += f"Embedded images: {result_data['embedded_images']['total_images']}\n"
            result_text += f"Full page images: {len(result_data['full_page_images'])}\n"
            result_text += f"Results saved to: {output_file}\n"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting images: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())