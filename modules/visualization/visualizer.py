import os
import base64
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from typing import List, Dict, Callable, Optional, Tuple, Union
from pathlib import Path
import uuid
from io import BytesIO
import matplotlib
import requests
import json
from google import genai
from google.genai import types
matplotlib.use('Agg')  
from modules.utils.async_buffer import AsyncBuffer
from modules.utils.image_helper import ImageHelper
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300

class Visualizer:

    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.figure_dir = output_dir / "figures"
        self.figure_dir.mkdir(exist_ok=True)
    
    async def generate_image_for_topic(self, topic: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        buffer.add_log(f"Generating visualization for {topic}", high_level=True)
        safe_topic = self._safe_filename(topic)
        figure_path = str(self.figure_dir / f"figure_{safe_topic}.png")
        try:
            viz_type = await self._determine_visualization_type(topic, query_func, buffer)
            
            if viz_type == "chart":
                return await self._generate_chart(topic, figure_path, buffer, query_func)
            elif viz_type == "network":
                return await self._generate_network_graph(topic, figure_path, buffer, query_func)
            elif viz_type == "process":
                return await self._generate_process_diagram(topic, figure_path, buffer, query_func)
            elif viz_type == "comparison":
                return await self._generate_comparison_chart(topic, figure_path, buffer, query_func)
            else:
                return await self._generate_concept_map(topic, figure_path, buffer, query_func)
                
        except Exception as e:
            buffer.add_log(f"Error generating chart: {str(e)}", high_level=True)
            buffer.add_log(f"Failed to generate visualization for {topic}, trying fallback", high_level=True)
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _determine_visualization_type(self, topic: str, query_func: Callable, buffer: AsyncBuffer) -> str:

        prompt = f"""
Analyze this topic: "{topic}"
Which visualization type would be most appropriate?
Choose ONE from these options:
1. "chart" - For numerical data, trends, statistics
2. "network" - For interconnected concepts, relationships
3. "process" - For sequential steps, workflows, algorithms
4. "comparison" - For comparing multiple items/approaches
5. "concept" - For hierarchical knowledge organization

Reply with ONLY the visualization type in quotes (e.g., "chart").
"""
        
        try:
            result = await query_func(prompt, buffer)
            result = result.lower().strip()
            
            if "chart" in result:
                return "chart"
            elif "network" in result:
                return "network"
            elif "process" in result:
                return "process"
            elif "comparison" in result:
                return "comparison"
            else:
                return "concept"
                
        except Exception as e:
            buffer.add_log(f"Error determining visualization type: {str(e)}")
            return "concept"  # Default to concept map
    
    async def _generate_chart(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        prompt = f"""
Create a data visualization for: "{topic}"
Generate synthetic data that would be realistic for this topic.
Return a JSON object with:
1. "chart_type": bar, line, pie, or scatter
2. "title": Chart title
3. "x_label": X-axis label
4. "y_label": Y-axis label
5. "x_data": Array of values (use integers for numeric values, strings for categories)
6. "y_data": Array of values (use ONLY integers for all values)
7. "series_name": Name for the data series

IMPORTANT: y_data MUST contain only integer values, not floats or strings.

For example:
```json
{{
  "chart_type": "bar",
  "title": "Security Incident Types",
  "x_label": "Incident Type", 
  "y_label": "Frequency",
  "x_data": ["Phishing", "Malware", "DDoS", "Data Breach"],
  "y_data": [45, 30, 15, 10],
  "series_name": "Incidents"
}}
```
```json
{{
  "chart_type": "line",
  "title": "Algorithm Performance Over Time",
  "x_label": "Year", 
  "y_label": "Efficiency",
  "x_data": [2018, 2019, 2020, 2021, 2022],
  "y_data": [65, 78, 82, 91, 94],
  "series_name": "Performance Score"
}}
```

Only provide valid JSON data with integer y_data values.
"""
        
        try:
            chart_data_str = await query_func(prompt, buffer)
            import json
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', chart_data_str, re.DOTALL)
            if (json_match):
                chart_data_str = json_match.group(1).strip()
            
            chart_data = json.loads(chart_data_str)
            y_data = [int(y) for y in chart_data["y_data"]]
            x_data = chart_data["x_data"]
            if (chart_data["chart_type"] in ["line", "scatter"]):
                try:
                    x_data = [int(x) if isinstance(x, (int, float)) or (isinstance(x, str) and x.isdigit()) else x 
                             for x in chart_data["x_data"]]
                except (ValueError, TypeError):
                    pass
            plt.figure(figsize=(10, 6), dpi=150)  # Increased DPI
            
            if (chart_data["chart_type"] == "bar"):
                plt.bar(x_data, y_data, color='royalblue')
                if (len(x_data) > 4):
                    plt.xticks(rotation=45, ha='right')
            elif (chart_data["chart_type"] == "line"):
                plt.plot(x_data, y_data, marker='o', color='forestgreen', 
                        linewidth=2, markersize=8)
            elif (chart_data["chart_type"] == "pie"):
                plt.pie(y_data, labels=x_data, autopct='%1.1f%%', 
                      startangle=90, shadow=True, textprops={'fontsize': 12})
            elif (chart_data["chart_type"] == "scatter"):
                plt.scatter(x_data, y_data, color='darkorange', 
                          s=120, alpha=0.7, edgecolors='black')
            
            plt.title(chart_data["title"], fontsize=16, pad=20)
            
            if (chart_data["chart_type"] != "pie"):
                plt.xlabel(chart_data["x_label"], fontsize=12, labelpad=10)
                plt.ylabel(chart_data["y_label"], fontsize=12, labelpad=10)
                plt.grid(True, linestyle='--', alpha=0.7)
                
            plt.tight_layout(pad=3.0)
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            optimized_path = ImageHelper.optimize_image(figure_path)
            
            buffer.add_log(f"Successfully generated chart visualization for {topic}")
            return optimized_path
            
        except Exception as e:
            buffer.add_log(f"Error generating chart: {str(e)}")
            import traceback
            buffer.add_log(f"Detailed error: {traceback.format_exc()}")
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _generate_network_graph(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        prompt = f"""
Create a network visualization for: "{topic}"
Generate a realistic network of concepts related to this topic.
Return a JSON object with:
1. "title": Network title
2. "nodes": Array of node objects with "name" and "weight" (integers only, from 1-10)
3. "edges": Array of edge objects with "source", "target", and "weight" (integers only, from 1-5)

IMPORTANT:
- All weights MUST be integers (whole numbers), not floats or strings
- For weights, use only values like 1, 2, 3, etc. (not 1.5, 2.3, etc.)

For example:
```json
{{
  "title": "Cybersecurity Concepts",
  "nodes": [
    {{"name": "Encryption", "weight": 10}},
    {{"name": "Authentication", "weight": 8}},
    {{"name": "Firewall", "weight": 7}},
    {{"name": "Access Control", "weight": 6}},
    {{"name": "Vulnerability", "weight": 5}}
  ],
  "edges": [
    {{"source": "Encryption", "target": "Authentication", "weight": 4}},
    {{"source": "Authentication", "target": "Access Control", "weight": 5}},
    {{"source": "Firewall", "target": "Access Control", "weight": 3}},
    {{"source": "Vulnerability", "target": "Firewall", "weight": 2}}
  ]
}}
```

Provide only 5-8 nodes and appropriate connecting edges. Ensure all node names referenced in edges exist in the nodes array.
Only provide valid JSON with integer weights.
"""
        
        try:
            network_data_str = await query_func(prompt, buffer)
            import json
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', network_data_str, re.DOTALL)
            if (json_match):
                network_data_str = json_match.group(1).strip()
            
            network_data = json.loads(network_data_str)
            G = nx.Graph()
            node_weights = {}
            for node in network_data["nodes"]:
                weight = int(node.get("weight", 5))
                node_name = node["name"]
                G.add_node(node_name, weight=weight)
                node_weights[node_name] = weight * 100
            edge_weights = {}
            for edge in network_data["edges"]:
                weight = int(edge.get("weight", 1))
                source = edge["source"]
                target = edge["target"]
                G.add_edge(source, target, weight=weight)
                edge_weights[(source, target)] = weight
                edge_weights[(target, source)] = weight  # Store both directions for undirected graph
            plt.figure(figsize=(12, 8), dpi=150)
            pos = nx.spring_layout(G, k=0.15, seed=42)
            node_sizes = []
            for node in G.nodes():
                node_sizes.append(node_weights.get(node, 500))
            edge_widths = []
            for u, v in G.edges():
                edge_widths.append(edge_weights.get((u, v), 1))
            nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.8)
            nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color='gray', alpha=0.5, arrows=True)
            label_pos = {node: (coords[0], coords[1] + 0.02) for node, coords in pos.items()}
            nx.draw_networkx_labels(G, label_pos, font_size=11, font_family='sans-serif',
                                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=2))
            
            plt.title(network_data["title"], fontsize=16, pad=20)
            plt.axis('off')  # Turn off axis
            plt.tight_layout(pad=3.0)  
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            optimized_path = ImageHelper.optimize_image(figure_path)
            
            buffer.add_log(f"Successfully generated network visualization for {topic}")
            return optimized_path
            
        except Exception as e:
            buffer.add_log(f"Error generating network graph: {str(e)}")
            import traceback
            buffer.add_log(f"Detailed error: {traceback.format_exc()}")
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _generate_process_diagram(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        prompt = f"""
Create a process flow diagram for: "{topic}"
Generate a realistic sequence of steps related to this topic.
Return a JSON object with:
1. "title": Process title
2. "steps": Array of step objects with "name" and "description"
3. "connections": Array of connection objects with "from" and "to" 

For example:
```json
{{
  "title": "Data Encryption Process",
  "steps": [
    {{"name": "Plaintext", "description": "Original readable data"}},
    {{"name": "Key Generation", "description": "Create encryption key"}},
    {{"name": "Encryption Algorithm", "description": "Apply the cipher"}},
    {{"name": "Ciphertext", "description": "Encrypted data output"}},
    {{"name": "Transmission", "description": "Send encrypted data"}}
  ],
  "connections": [
    {{"from": "Plaintext", "to": "Encryption Algorithm"}},
    {{"from": "Key Generation", "to": "Encryption Algorithm"}},
    {{"from": "Encryption Algorithm", "to": "Ciphertext"}},
    {{"from": "Ciphertext", "to": "Transmission"}}
  ]
}}
```

Provide 4-7 process steps. Ensure all step names referenced in connections exist in the steps array.
Only provide valid JSON.
"""
        
        try:
            process_data_str = await query_func(prompt, buffer)
            import json
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', process_data_str, re.DOTALL)
            if (json_match):
                process_data_str = json_match.group(1).strip()
            
            process_data = json.loads(process_data_str)
            G = nx.DiGraph()
            descriptions = {}
            for step in process_data["steps"]:
                G.add_node(step["name"])
                descriptions[step["name"]] = step["description"]
            for conn in process_data["connections"]:
                G.add_edge(conn["from"], conn["to"])
            
            plt.figure(figsize=(12, 8), dpi=100)
            pos = nx.nx_pydot.graphviz_layout(G, prog='dot', root=process_data["steps"][0]["name"])
            node_size = 3000
            nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color='lightblue', 
                                  node_shape='o', edgecolors='darkblue', alpha=0.8)
            nx.draw_networkx_edges(G, pos, width=1.5, edge_color='gray', 
                                  arrowstyle='-|>', arrowsize=20, arrows=True)
            nx.draw_networkx_labels(G, pos, font_size=11, font_family='sans-serif', font_weight='bold')
            for node, (x, y) in pos.items():
                if (node in descriptions):
                    description = descriptions[node]
                    if (len(description) > 30):
                        description = description[:27] + "..."
                    plt.text(x, y-30, description, ha='center', va='center', 
                            fontsize=8, wrap=True, bbox=dict(facecolor='white', alpha=0.7))
            
            plt.title(process_data["title"], fontsize=16, pad=20)
            plt.axis('off')
            plt.tight_layout(pad=3.0)
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            optimized_path = ImageHelper.optimize_image(figure_path)
            
            buffer.add_log(f"Successfully generated process diagram for {topic}")
            return optimized_path
            
        except Exception as e:
            buffer.add_log(f"Error generating process diagram: {str(e)}")
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _generate_comparison_chart(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        prompt = f"""
Create a comparison chart for: "{topic}"
Generate synthetic comparison data for items related to this topic.
Return a JSON object with:
1. "title": Chart title
2. "items": Array of items being compared
3. "criteria": Array of comparison criteria
4. "scores": 2D array of ONLY INTEGER scores (0-10) where scores[i][j] is the score of items[i] on criteria[j]

IMPORTANT: All scores must be integers (whole numbers) between 0-10, not floats or strings.

For example:
```json
{{
  "title": "Comparison of Encryption Algorithms",
  "items": ["AES", "RSA", "Blowfish", "3DES"],
  "criteria": ["Security", "Performance", "Implementation Ease", "Key Size"],
  "scores": [
    [9, 7, 8, 6],
    [10, 5, 6, 9],
    [8, 8, 7, 7],
    [7, 4, 6, 8]
  ]
}}
```

Provide 3-5 items and 3-5 criteria. Ensure the scores array dimensions match the items and criteria arrays.
Only provide valid JSON with integer scores.
"""
        
        try:
            comparison_data_str = await query_func(prompt, buffer)
            import json
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', comparison_data_str, re.DOTALL)
            if (json_match):
                comparison_data_str = json_match.group(1).strip()
            
            comparison_data = json.loads(comparison_data_str)
            items = comparison_data["items"]
            criteria = comparison_data["criteria"]
            raw_scores = comparison_data["scores"]
            scores = []
            for row in raw_scores:
                int_row = [int(score) for score in row]
                scores.append(int_row)
            N = len(criteria)
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Close the loop
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_rlabel_position(0)
            plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="grey", size=8)
            plt.ylim(0, 10)
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for i, (item, score_row) in enumerate(zip(items, scores)):
                values = score_row.copy()
                values += values[:1]  # Close the loop
                ax.plot(angles, values, linewidth=2, linestyle='solid', label=item, color=colors[i % len(colors)])
                ax.fill(angles, values, color=colors[i % len(colors)], alpha=0.1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(criteria, size=12)
            plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
            
            plt.title(comparison_data["title"], fontsize=16, y=1.08)
            plt.tight_layout()
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            optimized_path = ImageHelper.optimize_image(figure_path)
            
            buffer.add_log(f"Successfully generated comparison chart for {topic}")
            return optimized_path
            
        except Exception as e:
            buffer.add_log(f"Error generating comparison chart: {str(e)}")
            import traceback
            buffer.add_log(f"Detailed error: {traceback.format_exc()}")
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _generate_concept_map(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        prompt = f"""
Create a concept map for: "{topic}"
Generate a hierarchical structure of concepts related to this topic.
Return a JSON object with:
1. "title": Map title
2. "main_concept": Central concept name
3. "branches": Array of branch objects with "name" and "subconcepts" array

For example:
```json
{{
  "title": "Machine Learning Concepts",
  "main_concept": "Machine Learning",
  "branches": [
    {{"name": "Supervised Learning",
      "subconcepts": ["Classification", "Regression", "Neural Networks"]}},
    {{"name": "Unsupervised Learning",
      "subconcepts": ["Clustering", "Dimensionality Reduction"]}},
    {{"name": "Evaluation Metrics",
      "subconcepts": ["Accuracy", "Precision", "Recall"]}}
  ]
}}
```

Provide 3-5 main branches with 2-4 subconcepts each. Keep concept names brief.
Only provide valid JSON.
"""
        
        try:
            concept_data_str = await query_func(prompt, buffer)
            import json
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', concept_data_str, re.DOTALL)
            if (json_match):
                concept_data_str = json_match.group(1).strip()
            
            concept_data = json.loads(concept_data_str)
            G = nx.Graph()
            main_concept = concept_data["main_concept"]
            G.add_node(main_concept, level=0)
            for i, branch in concept_data["branches"]:
                branch_name = branch["name"]
                G.add_node(branch_name, level=1)
                G.add_edge(main_concept, branch_name)
                
                for subconcept in branch["subconcepts"]:
                    G.add_node(subconcept, level=2)
                    G.add_edge(branch_name, subconcept)
            plt.figure(figsize=(12, 8), dpi=100)
            pos = nx.nx_agraph.graphviz_layout(G, prog="twopi", root=main_concept)
            node_levels = nx.get_node_attributes(G, 'level')
            colors = []
            sizes = []
            
            for node in G.nodes():
                level = node_levels.get(node, 0)
                if (level == 0):  # Main concept
                    colors.append('#1f77b4')  # Blue
                    sizes.append(2000)
                elif (level == 1):  # Branches
                    colors.append('#ff7f0e')  # Orange
                    sizes.append(1500)
                else:  # Subconcepts
                    colors.append('#2ca02c')  # Green
                    sizes.append(1000)
            nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=colors, alpha=0.8)
            nx.draw_networkx_edges(G, pos, width=1.5, edge_color='gray', alpha=0.5)
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold', font_family='sans-serif',
                                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=2))
            
            plt.title(concept_data["title"], fontsize=16, pad=20)
            plt.axis('off')
            plt.tight_layout(pad=3.0)
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            optimized_path = ImageHelper.optimize_image(figure_path)
            
            buffer.add_log(f"Successfully generated concept map for {topic}")
            return optimized_path
            
        except Exception as e:
            buffer.add_log(f"Error generating concept map: {str(e)}")
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
    
    async def _generate_fallback_visualization(self, topic: str, figure_path: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        try:
            plt.figure(figsize=(10, 6), dpi=100)
            plt.gca().set_facecolor('#f8f9fa')
            plt.text(0.5, 0.8, f"{topic}", fontsize=20, ha='center', fontweight='bold')
            plt.text(0.5, 0.6, "Key Concepts", fontsize=16, ha='center')
            topic_words = topic.split()
            bullet_points = []
            if (len(topic_words) >= 3):
                bullet_points = [
                    f"• {topic_words[0]} fundamentals",
                    f"• {topic_words[-1]} applications",
                    f"• Current research trends"
                ]
            else:
                bullet_points = [
                    "• Fundamental principles",
                    "• Practical applications",
                    "• Recent developments"
                ]
            for i, point in bullet_points:
                plt.text(0.3, 0.5 - (i * 0.1), point, fontsize=14, ha='left')
            
            plt.axis('off')  # Turn off the axis
            plt.gca().spines['top'].set_visible(True)
            plt.gca().spines['right'].set_visible(True)
            plt.gca().spines['bottom'].set_visible(True)
            plt.gca().spines['left'].set_visible(True)
            plt.gca().spines['top'].set_color('#dddddd')
            plt.gca().spines['right'].set_color('#dddddd')
            plt.gca().spines['bottom'].set_color('#dddddd')
            plt.gca().spines['left'].set_color('#dddddd')
            plt.savefig(figure_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            buffer.add_log(f"Created fallback visualization for {topic}")
            return figure_path
            
        except Exception as e:
            buffer.add_log(f"Error creating fallback visualization: {str(e)}")
            return ""  # Return empty string if even the fallback fails
    
    def embed_image_base64(self, image_path: str) -> str:

        return ImageHelper.convert_to_base64(image_path)
    
    def _safe_filename(self, name: str) -> str:

        import re
        name = re.sub(r'[^\w\s-]', '', name.lower())
        name = re.sub(r'[\s]+', '-', name)
        if (len(name) > 40):
            name = name[:37] + "..."
        short_id = str(uuid.uuid4())[:8]
        return f"{short_id}_{name}"
    
    async def _search_image(self, topic: str, buffer: AsyncBuffer) -> Optional[str]:

        search_url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "uselang": "en",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap|drawing -fileres:0 {topic}",
            "gsrlimit": 1,
            "gsroffset": 0,
            "gsrinfo": "totalhits|suggestion",
            "gsrprop": "size|wordcount|timestamp|snippet",
            "prop": "info|imageinfo|entityterms",
            "inprop": "url",
            "gsrnamespace": 6,
            "iiprop": "url|size|mime",
            "iiurlheight": 180,
            "wbetterms": "label"
        }
        
        try:
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                buffer.add_log(f"No images found for topic: {topic}")
                return None
            
            for page_id, page in pages.items():
                image_info = page.get("imageinfo", [])
                if image_info:
                    image_url = image_info[0].get("url")
                    if image_url:
                        buffer.add_log(f"Found image for topic: {topic}")
                        return image_url
            
            buffer.add_log(f"No suitable images found for topic: {topic}")
            return None
        
        except Exception as e:
            buffer.add_log(f"Error searching for image: {str(e)}")
            return None
    
    async def _verify_image_with_gemini(self, image_url: str, topic: str, buffer: AsyncBuffer) -> bool:

        try:
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            files = [
                client.files.upload(file=BytesIO(base64.b64decode(encoded_image)))
            ]
            
            model = "gemini-2.0-flash"
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=files[0].uri,
                            mime_type=files[0].mime_type,
                        ),
                        types.Part.from_text(text=f"Verify if this image matches the topic: {topic}"),
                    ],
                )
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
                response_mime_type="text/plain",
            )
            
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if "yes" in chunk.text.lower():
                    buffer.add_log(f"Image verified for topic: {topic}")
                    return True
            
            buffer.add_log(f"Image not verified for topic: {topic}")
            return False
        
        except Exception as e:
            buffer.add_log(f"Error verifying image with Gemini: {str(e)}")
            return False
    
    async def generate_image_for_topic_with_verification(self, topic: str, buffer: AsyncBuffer, query_func: Callable) -> str:

        buffer.add_log(f"Generating visualization for {topic} with image verification", high_level=True)
        safe_topic = self._safe_filename(topic)
        figure_path = str(self.figure_dir / f"figure_{safe_topic}.png")
        try:
            viz_type = await self._determine_visualization_type(topic, query_func, buffer)
            
            if viz_type == "chart":
                return await self._generate_chart(topic, figure_path, buffer, query_func)
            elif viz_type == "network":
                return await self._generate_network_graph(topic, figure_path, buffer, query_func)
            elif viz_type == "process":
                return await self._generate_process_diagram(topic, figure_path, buffer, query_func)
            elif viz_type == "comparison":
                return await self._generate_comparison_chart(topic, figure_path, buffer, query_func)
            else:
                return await self._generate_concept_map(topic, figure_path, buffer, query_func)
                
        except Exception as e:
            buffer.add_log(f"Error generating chart: {str(e)}", high_level=True)
            buffer.add_log(f"Failed to generate visualization for {topic}, trying fallback", high_level=True)
            return await self._generate_fallback_visualization(topic, figure_path, buffer, query_func)
        image_url = await self._search_image(topic, buffer)
        if image_url:
            is_verified = await self._verify_image_with_gemini(image_url, topic, buffer)
            if is_verified:
                buffer.add_log(f"Using verified image for topic: {topic}")
                return image_url
        
        buffer.add_log(f"No verified image found for topic: {topic}")
        return figure_path
