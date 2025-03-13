from typing import Dict, List, Any, Callable, Optional, Union
import json
import re
from modules.utils.async_buffer import AsyncBuffer

class TableGenerator:

    
    async def generate_table_from_text(self, text: str, topic: str, 
                                     buffer: AsyncBuffer, 
                                     query_func: Callable) -> Dict[str, Any]:
        buffer.add_log(f"Generating table for topic: {topic}")
        prompt = f"""
You are a research assistant helping to create a data table for a research paper on "{topic}".
Based on the following text, create a markdown table that organizes the information effectively.

TEXT:
{text[:2500]}

Instructions:
1. Extract key information that would benefit from tabular presentation
2. Create a table with 2-5 columns and 3-10 rows (as appropriate)
3. Include meaningful column headers
4. Make sure the rows contain comparable data
5. Provide a descriptive caption for the table

Return a JSON object with this structure:
{{
  "caption": "Table caption here",
  "headers": ["Column1", "Column2", ...],
  "rows": [
    ["Row1Col1", "Row1Col2", ...],
    ["Row2Col1", "Row2Col2", ...],
    ...
  ]
}}

Make sure the JSON is properly formatted with quotes around keys and string values.
"""
        
        try:
            table_json = await query_func(prompt, buffer)
            if "```json" in table_json:
                table_json = re.search(r'```json(.*?)```', table_json, re.DOTALL)
                if table_json:
                    table_json = table_json.group(1).strip()
            elif "```" in table_json:
                table_json = re.search(r'```(.*?)```', table_json, re.DOTALL)
                if table_json:
                    table_json = table_json.group(1).strip()
            table_json = table_json.strip()
            if not table_json.startswith('{'):
                start_idx = table_json.find('{')
                if start_idx >= 0:
                    table_json = table_json[start_idx:]
            end_idx = table_json.rfind('}')
            if end_idx >= 0:
                table_json = table_json[:end_idx+1]
            
            try:
                table_data = json.loads(table_json)
            except json.JSONDecodeError:
                buffer.add_log("JSON parsing failed, attempting manual extraction")
                table_data = self._manual_extract_table(table_json)
            markdown = self.table_to_markdown(table_data)
            
            result = {
                "caption": table_data.get("caption", f"Data table related to {topic}"),
                "headers": table_data.get("headers", []),
                "rows": table_data.get("rows", []),
                "markdown": markdown
            }
            
            buffer.add_log(f"Successfully generated table with {len(table_data.get('rows', []))} rows and {len(table_data.get('headers', []))} columns")
            return result
            
        except Exception as e:
            buffer.add_log(f"Error generating table: {str(e)}")
            return self._generate_fallback_table(topic)
    
    def _manual_extract_table(self, text: str) -> Dict:

        result = {"caption": "", "headers": [], "rows": []}
        caption_match = re.search(r'"caption"\s*:\s*"([^"]+)"', text)
        if caption_match:
            result["caption"] = caption_match.group(1)
        headers_match = re.search(r'"headers"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if headers_match:
            headers_str = headers_match.group(1)
            headers = re.findall(r'"([^"]+)"', headers_str)
            result["headers"] = headers
        rows_section = re.search(r'"rows"\s*:\s*\[(.*?)\](?=\s*[,}])', text, re.DOTALL)
        if rows_section:
            rows_str = rows_section.group(1)
            row_patterns = re.findall(r'\[(.*?)\]', rows_str, re.DOTALL)
            
            rows = []
            for pattern in row_patterns:
                cells = re.findall(r'"([^"]+)"', pattern)
                if cells:
                    rows.append(cells)
                    
            result["rows"] = rows
            
        return result
    
    def _generate_fallback_table(self, topic: str) -> Dict[str, Any]:

        headers = ["Aspect", "Description", "Importance"]
        rows = [
            [f"{topic} Component 1", "Primary element", "High"],
            [f"{topic} Component 2", "Secondary element", "Medium"],
            [f"{topic} Component 3", "Supporting element", "Medium"]
        ]
        
        markdown = self.table_to_markdown({
            "caption": f"Key components of {topic}",
            "headers": headers,
            "rows": rows
        })
        
        return {
            "caption": f"Key components of {topic}",
            "headers": headers,
            "rows": rows,
            "markdown": markdown
        }
            
    def table_to_markdown(self, table_data: Dict[str, Any]) -> str:

        if not table_data or "headers" not in table_data or "rows" not in table_data:
            return ""
            
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        caption = table_data.get("caption", "")
        
        if not headers or not rows:
            return ""
        html_table = f"""<div class="table-wrapper">
<table class="markdown-table">
<thead>
<tr>
"""
        for header in headers:
            html_table += f"<th>{header}</th>\n"
        
        html_table += """</tr>
</thead>
<tbody>
"""
        for row in rows:
            while len(row) < len(headers):
                row.append("")
                
            if len(row) > len(headers):
                row = row[:len(headers)]  # Truncate if too many cells
                
            html_table += "<tr>\n"
            for cell in row:
                html_table += f"<td>{str(cell).strip()}</td>\n"
            html_table += "</tr>\n"
            
        html_table += """</tbody>
</table>
"""
        if caption:
            html_table += f"<div class='caption'>{caption}</div>\n"
            
        html_table += "</div>\n"
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---" for _ in headers]) + " |"
        data_rows = []
        for row_data in rows:
            clean_row = [str(cell).replace("|", "\\|") for cell in row_data]
            data_rows.append("| " + " | ".join(clean_row) + " |")
        markdown_table = "\n".join([header_row, separator] + data_rows)
        
        if caption:
            markdown_table += f"\n\n*{caption}*\n"
        return f"""
{html_table}

<!-- Markdown table version (fallback):
{markdown_table}
-->
"""
