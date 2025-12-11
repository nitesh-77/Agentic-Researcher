import re
import json
import networkx as nx
from pyvis.network import Network
from typing import List, Dict, Set
from datetime import datetime
import tempfile
import os

class KnowledgeGraphGenerator:
    """Generate interactive knowledge graphs from research reports"""

    def __init__(self):
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract key entities from research report
        Returns dict with categories: technologies, organizations, people, concepts
        """
        # Simple but effective entity extraction patterns
        entity_patterns = {
            'technologies': [
                r'\b([A-Z][a-z]*[0-9]*\s*(?:Chip|Processor|Architecture|Technology|Battery|Protocol))\b',
                r'\b([A-Z]{2,}[0-9]*(?:\s+)*[A-Z]*[0-9]*)\b',  # M4, SSD, etc.
                r'\b(?:\w+\s+)*(?:Technology|System|Device|Component)\b'
            ],
            'organizations': [
                r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s*(?:Inc|Corp|Company|Labs|Research|University))\b',
                r'\b(?:Apple|Google|Microsoft|Intel|AMD|NVIDIA|Toyota|QuantumScape|Tesla)\b'
            ],
            'concepts': [
                r'\b(?:Solid State|Lithium Ion|Quantum Computing|Machine Learning|AI|Neural Network)\b',
                r'\b(?:Breakthrough|Innovation|Revolutionary|Advanced|Next Generation)\b'
            ]
        }

        entities = {
            'technologies': set(),
            'organizations': set(),
            'concepts': set(),
            'keywords': set()
        }

        # Extract with patterns
        for category, patterns in entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if len(match) > 3:  # Filter very short matches
                        entities[category].add(match.strip())

        # Extract key phrases (capitalized words)
        key_phrases = re.findall(r'\b(?:[A-Z][a-z]*\s*){2,}\b', text)
        entities['keywords'].update([phrase.strip() for phrase in key_phrases if 10 > len(phrase) > 4])

        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in entities.items()}

    def create_network_graph(self, entities: Dict[str, List[str]], text: str) -> nx.Graph:
        """Create a network graph from extracted entities"""
        G = nx.Graph()

        # Add nodes with categories
        categories = {
            'technologies': '#FF6B6B',  # Red
            'organizations': '#4ECDC4',  # Teal
            'concepts': '#45B7D1',  # Blue
            'keywords': '#96CEB4'  # Green
        }

        for category, items in entities.items():
            color = categories.get(category, '#CCCCCC')
            for item in items[:15]:  # Limit to top 15 per category
                G.add_node(
                    item,
                    category=category,
                    color=color,
                    size=20 + len(item) * 0.5
                )

        # Create edges based on co-occurrence in text
        entity_list = []
        for category, items in entities.items():
            entity_list.extend(items[:10])

        # Simple co-occurrence analysis
        for i, entity1 in enumerate(entity_list):
            for j, entity2 in enumerate(entity_list[i+1:], i+1):
                if entity1 in text and entity2 in text:
                    # Calculate rough proximity (simple distance measure)
                    pos1 = text.find(entity1)
                    pos2 = text.find(entity2)
                    if abs(pos1 - pos2) < 1000:  # Within ~1000 characters
                        G.add_edge(entity1, entity2, weight=1.0)

        return G

    def generate_interactive_graph(self, report_text: str, session_id: str) -> str:
        """
        Generate an interactive HTML graph from research report
        Returns path to the generated HTML file
        """
        print("🕸️ Generating interactive knowledge graph")

        # Extract entities
        entities = self.extract_entities(report_text)
        print(f"📊 Extracted entities: {sum(len(v) for v in entities.values())} total")

        # Create network graph
        network_graph = self.create_network_graph(entities, report_text)

        # Create Pyvis network
        net = Network(
            height="600px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#333333",
            notebook=False
        )

        # Transfer nodes and edges
        net.from_nx(network_graph)

        # Configure physics for better visualization
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08,
                    "damping": 0.4,
                    "avoidOverlap": 0.5
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "hideEdgesOnDrag": true
            },
            "nodes": {
                "font": {
                    "size": 14
                }
            }
        }
        """)

        # Add title and legend
        html_content = f"""
        <html>
        <head>
            <title>Research Knowledge Graph - Session {session_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .legend {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: white;
                    padding: 15px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .legend-item {{ display: flex; align-items: center; margin: 5px 0; }}
                .legend-color {{
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    margin-right: 10px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 20px;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Research Knowledge Graph</h2>
                <p>Interactive visualization of key concepts and entities from your research</p>
            </div>
            <div class="legend">
                <h4>Legend</h4>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #FF6B6B;"></div>
                    <span>Technologies</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #4ECDC4;"></div>
                    <span>Organizations</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #45B7D1;"></div>
                    <span>Concepts</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #96CEB4;"></div>
                    <span>Keywords</span>
                </div>
            </div>
        """

        # Save the graph
        filename = f"knowledge_graph_{session_id}.html"
        filepath = os.path.join(self.temp_dir, filename)

        # Combine with network HTML
        net_html = net.generate_html()

        # Extract just the network part (skip the head/body tags)
        net_content = net_html[net_html.find('<div id="mynetwork"'):net_html.rfind('</script>') + 9]

        final_html = f"""{html_content}
            {net_content}
        </body>
        </html>"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_html)

        print(f"🎯 Knowledge graph saved: {filepath}")
        return filepath

    def generate_entity_summary(self, entities: Dict[str, List[str]]) -> str:
        """Generate a text summary of extracted entities"""
        summary = "## Key Entities Discovered\n\n"

        for category, items in entities.items():
            if items:
                summary += f"### {category.title()}\n"
                for item in items[:10]:  # Top 10 per category
                    summary += f"- {item}\n"
                summary += "\n"

        return summary.strip() if summary.strip() else "No key entities identified in the research."