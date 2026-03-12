"""Notion output for Atlas Twitter Analytics."""

import os
import requests
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

def create_report_page(parent_page_id, title, data):
    """Create a Notion page with Twitter analytics report."""
    
    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Week-over-Week Summary"}}]
            }
        }
    ]
    
    # Add table for each client
    for client, stats in data.items():
        children.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": client}}]
            }
        })
        
        children.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 4,
                "has_column_header": True,
                "has_row_header": False,
                "children": [
                    {
                        "object": "block",
                        "type": "table_row",
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Metric"}}],
                                [{"type": "text", "text": {"content": "This Week"}}],
                                [{"type": "text", "text": {"content": "Last Week"}}],
                                [{"type": "text", "text": {"content": "Change"}}]
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "table_row", 
                        "table_row": {
                            "cells": [
                                [{"type": "text", "text": {"content": "Avg Engagement Rate"}}],
                                [{"type": "text", "text": {"content": f"{stats.get('this_week', 0):.2f}%"}}],
                                [{"type": "text", "text": {"content": f"{stats.get('last_week', 0):.2f}%"}}],
                                [{"type": "text", "text": {"content": f"{stats.get('change', 0):+.1f}%"}}]
                            ]
                        }
                    }
                ]
            }
        })
    
    payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        "children": children
    }
    
    response = requests.post(
        f"{BASE_URL}/pages",
        headers=HEADERS,
        json=payload
    )
    
    return response.json()
