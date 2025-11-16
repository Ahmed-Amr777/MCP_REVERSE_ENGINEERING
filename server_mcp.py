import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
import PyPDF2
import os

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

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())