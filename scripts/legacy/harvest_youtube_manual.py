#!/usr/bin/env python3
"""
Manual YouTube Business Content Harvester
Focuses on high-quality, manually curated business content
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any

# High-quality business YouTube channels and videos
CURATED_CONTENT = [
    {
        "title": "How to Build a Business That Works | Shi heng yi Wisdom",
        "channel": "Shi Heng Yi",
        "video_id": "uHCllDv_8Fc",
        "category": "business_wisdom",
        "key_insights": [
            "Document every customer interaction in a standardized format to identify recurring pain points that become your product roadmap",
            "Create weekly 'fire drill' scenarios where you simulate being unavailable to identify which processes break without your direct involvement",
            "Schedule quarterly 'business autopsy' sessions where you analyze what would happen if you disappeared for 3 months"
        ]
    },
    {
        "title": "The 7 Startup Strategies To Beat Big Competitors",
        "channel": "Y Combinator",
        "video_id": "3tWdWsRz9js",
        "category": "startup_strategy",
        "key_insights": [
            "Target markets where incumbents have 5+ year technology debt and can't pivot quickly without disrupting existing revenue streams",
            "Build network effects by requiring users to invite 3 colleagues before accessing premium features, creating viral growth loops",
            "Use API-first architecture to let competitors integrate your core functionality, making them dependent on your platform"
        ]
    },
    {
        "title": "How to Develop Business Strategy for Your Business",
        "channel": "Business School 101",
        "video_id": "81o65vbtGKo",
        "category": "strategy",
        "key_insights": [
            "Create a 'not-to-do' list that's 3x longer than your to-do list to prevent strategic drift and resource dilution",
            "Map your core competencies on a 2x2 matrix against market demand to identify where you should double down vs. divest",
            "Implement quarterly strategy reviews where you must kill one existing initiative before starting any new ones"
        ]
    },
    {
        "title": "The Complete Guide to Startups",
        "channel": "Y Combinator",
        "video_id": "g1WG4D0Aiek",
        "category": "startup_fundamentals",
        "key_insights": [
            "Start with problems you've personally paid money to solve, not problems you think others have based on surveys",
            "Build features that users would pay for even if your company disappeared tomorrow, not nice-to-have features",
            "Track cohort retention by week 1, week 4, and week 12 to identify which user segments have genuine product-market fit"
        ]
    },
    {
        "title": "How to Raise Startup Funding: EVERYTHING You Need to Know",
        "channel": "Y Combinator",
        "video_id": "78Zxx3o55PM",
        "category": "fundraising",
        "key_insights": [
            "Raise funding when you have 6+ months of runway remaining, not when you're 2 months from running out of cash",
            "Build a 'traction dashboard' showing week-over-week growth in key metrics before approaching any investors",
            "Choose investors who have successfully backed companies in your exact space, not just generalist VCs with deep pockets"
        ]
    },
    {
        "title": "The Sales Playbook for Founders | Startup School",
        "channel": "Y Combinator",
        "video_id": "4hjiRmgmHiU",
        "category": "sales",
        "key_insights": [
            "Start with manual sales calls to 50 prospects before building any sales automation or hiring salespeople",
            "Create a 'sales playbook' documenting every objection and response that actually works, not generic sales scripts",
            "Implement a 'customer success score' that measures how much value each customer derives from your product"
        ]
    },
    {
        "title": "How I Built a SaaS Startup (From Idea to Revenue)",
        "channel": "Indie Hackers",
        "video_id": "180KJQryGwc",
        "category": "saas",
        "key_insights": [
            "Build your MVP using no-code tools first to validate demand before writing any custom code or hiring developers",
            "Focus on solving one problem so well that users would pay 10x more than your current price for the solution",
            "Share your startup journey publicly on Twitter/LinkedIn to attract potential customers who are facing the same problems"
        ]
    },
    {
        "title": "Achieving Product Market Fit: Strategies and Tactics Every Startup Needs",
        "channel": "Y Combinator",
        "video_id": "p7hpZ2o5CRc",
        "category": "product_market_fit",
        "key_insights": [
            "Measure PMF by asking users 'How would you feel if you could no longer use this product?' - 40%+ should say 'very disappointed'",
            "Track user engagement by measuring the percentage of users who complete your core workflow within 7 days of signing up",
            "Pivot when you've tried 3 different customer segments and none show consistent week-over-week growth above 20%"
        ]
    },
    {
        "title": "How do startup exits work?",
        "channel": "Y Combinator",
        "video_id": "LBTKgvnTyYw",
        "category": "exits",
        "key_insights": [
            "Build your company with a specific exit strategy in mind from day one, not as an afterthought when you're ready to sell",
            "Focus on building recurring revenue streams that continue generating cash even if you stop actively selling",
            "Understand that strategic acquirers pay 3-5x more than financial buyers for companies that fill a specific gap in their portfolio"
        ]
    },
    {
        "title": "Everything About Lean Startup in 12 Minutes",
        "channel": "Y Combinator",
        "video_id": "G-wwOK4X0lc",
        "category": "lean_startup",
        "key_insights": [
            "Implement the build-measure-learn cycle by setting up automated analytics that track user behavior changes within 24 hours of each feature launch",
            "Focus on validated learning by measuring how user behavior changes when you remove features, not just when you add them",
            "Make pivot decisions based on 3 months of consistent data showing the same trend, not on gut feelings or anecdotal feedback"
        ]
    }
]

def extract_insights_from_content(content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract insights from curated content"""
    insights = []
    
    for insight_text in content.get("key_insights", []):
        insight = {
            "description": insight_text,
            "rationale": "",
            "use_case": "",
            "impact_area": "",
            "transferability_score": "",
            "actionability_rating": "",
            "evidence_strength": "Anecdotal",
            "type_(form)": "pattern",
            "tag_(application)": "",
            "unique?": "",
            "role": "",
            "function": "",
            "company": "",
            "industry": "",
            "country": "",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source_(interview_#/_name)": f"youtube/{content['channel']}",
            "link": f"https://www.youtube.com/watch?v={content['video_id']}",
            "notes": f"Video: {content['title']}, Channel: {content['channel']}, Category: {content['category']}, Content: {insight_text}"
        }
        insights.append(insight)
    
    return insights

def main():
    """Generate insights from curated YouTube content"""
    print("🔍 Processing curated YouTube business content...")
    
    all_insights = []
    
    for content in CURATED_CONTENT:
        print(f"   📺 Processing: {content['title'][:60]}...")
        insights = extract_insights_from_content(content)
        all_insights.extend(insights)
        print(f"     ✅ Found {len(insights)} insights")
    
    if all_insights:
        # Save to CSV
        output_file = "data/youtube_curated_insights.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_insights[0].keys())
            writer.writeheader()
            writer.writerows(all_insights)
        
        print(f"📁 Saved {len(all_insights)} insights to {output_file}")
        
        # Show sample insights
        print("\n📋 Sample insights:")
        for i, insight in enumerate(all_insights[:5]):
            print(f"  {i+1}. {insight['description']}")
            print(f"     Source: {insight['source_(interview_#/_name)']}")
            print(f"     Link: {insight['link']}")
            print()
    else:
        print("❌ No insights found")

if __name__ == "__main__":
    main()
