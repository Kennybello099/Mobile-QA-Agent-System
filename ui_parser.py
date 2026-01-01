# ui_parser.py
import xml.etree.ElementTree as ET
import os
from typing import List, Dict

def get_clickable_elements(xml_path: str = "current_ui.xml") -> List[Dict]:
    """Parse UI XML and return list of clickable elements with text and center coordinates."""
    if not os.path.exists(xml_path):
        print(f"UI XML not found: {xml_path}")
        return []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        elements = []
        for node in root.iter('node'):
            if node.get('clickable') == 'true' or node.get('long-clickable') == 'true':
                bounds = node.get('bounds')
                text = node.get('text') or node.get('content-desc') or ""
                resource_id = node.get('resource-id') or ""
                if bounds:
                    coords = bounds.replace('[', '').replace(']', ',').split(',')
                    x1, y1, x2, y2 = map(int, coords[:4])
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    elements.append({
                        "index": len(elements),
                        "text": text.strip(),
                        "resource_id": resource_id,
                        "center": (center_x, center_y),
                        "bounds": (x1, y1, x2, y2)
                    })
        print(f"Found {len(elements)} clickable elements")
        return elements
    except Exception as e:
        print(f"XML parse error: {e}")
        return []