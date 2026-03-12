"""Notion integration for Atlas client reports."""

import os
import requests
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def get_headers():
    """Build request headers with a validated Notion token."""
    token = os.getenv("NOTION_API_KEY")
    if not token:
        raise ValueError("NOTION_API_KEY not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

def create_client_report(client_name, twitter_data, research_data=None):
    """Create a comprehensive Notion report for a client."""
    
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent_page_id:
        raise ValueError("NOTION_PARENT_PAGE_ID not set")
    
    title = f"{client_name} - Atlas Report ({datetime.now().strftime('%Y-%m-%d')})"
    
    children = [
        # Header
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": f"📊 {client_name} Analytics"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"}}]
            }
        },
        # Twitter Section
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🐦 Twitter Performance"}}]
            }
        }
    ]
    
    # Add Twitter metrics if available
    if twitter_data:
        fg = twitter_data.get("follower_growth", {})
        trend = "📈" if fg.get("trend") == "up" else "📉" if fg.get("trend") == "down" else "➡️"
        
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"{trend} Followers: {fg.get('current', 0):,} ({fg.get('growth', 0):+d}, {fg.get('growth_pct', 0):+.1f}%)"}}],
                "icon": {"emoji": "📊"}
            }
        })
        
        # Best posting times
        if twitter_data.get("best_times"):
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Best Posting Times"}}]
                }
            })
            
            for hour, engagement in twitter_data["best_times"][:3]:
                am_pm = "AM" if hour < 12 else "PM"
                display = hour if hour <= 12 else hour - 12
                if display == 0:
                    display = 12
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": f"{display} {am_pm}: {engagement:.1f} avg engagement"}}]
                    }
                })
        
        # Tweet performance table
        if twitter_data.get("tweet_types"):
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Tweet Type Performance"}}]
                }
            })
            
            children.append({
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": 3,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": [
                        {
                            "object": "block",
                            "type": "table_row",
                            "table_row": {
                                "cells": [
                                    [{"type": "text", "text": {"content": "Type"}}],
                                    [{"type": "text", "text": {"content": "Engagement Rate"}}],
                                    [{"type": "text", "text": {"content": "Count"}}]
                                ]
                            }
                        }
                    ] + [
                        {
                            "object": "block",
                            "type": "table_row",
                            "table_row": {
                                "cells": [
                                    [{"type": "text", "text": {"content": ttype}}],
                                    [{"type": "text", "text": {"content": f"{rate:.2f}%"}}],
                                    [{"type": "text", "text": {"content": str(count)}}]
                                ]
                            }
                        }
                        for ttype, rate, count in twitter_data["tweet_types"][:5]
                    ]
                }
            })
        
        # Actionable insights
        if twitter_data.get("insights"):
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "💡 Actionable Insights"}}]
                }
            })
            
            for insight in twitter_data["insights"]:
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": insight}}],
                        "checked": False
                    }
                })
    
    # Research Section
    if research_data:
        children.extend([
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🔍 Competitive Intelligence"}}]
                }
            }
        ])
        
        # Add research findings
        if research_data.get("findings"):
            for finding in research_data["findings"][:5]:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": finding}}]
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
        headers=get_headers(),
        json=payload
    )
    
    return response.json()

def create_weekly_summary(clients_data):
    """Create a weekly summary page with all clients."""
    
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent_page_id:
        raise ValueError("NOTION_PARENT_PAGE_ID not set")
    
    title = f"Atlas Weekly Summary - {datetime.now().strftime('%Y-%m-%d')}"
    
    children = [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": "📊 Weekly Client Summary"}}]
            }
        }
    ]
    
    # Summary table
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
                            [{"type": "text", "text": {"content": "Client"}}],
                            [{"type": "text", "text": {"content": "Followers"}}],
                            [{"type": "text", "text": {"content": "Growth"}}],
                            [{"type": "text", "text": {"content": "Status"}}]
                        ]
                    }
                }
            ] + [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [
                            [{"type": "text", "text": {"content": data["client"]}}],
                            [{"type": "text", "text": {"content": f"{data.get('followers', 0):,}"}}],
                            [{"type": "text", "text": {"content": f"{data.get('follower_growth', {}).get('growth_pct', 0):+.1f}%"}}],
                            [{"type": "text", "text": {"content": "📈" if data.get('follower_growth', {}).get('trend') == 'up' else "📉"}}]
                        ]
                    }
                }
                for data in clients_data
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
        headers=get_headers(),
        json=payload
    )
    
    return response.json()
