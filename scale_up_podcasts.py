#!/usr/bin/env python3
"""
Scale Up Podcast Harvester - Higher Limits for More Insights
Scales up the existing podcast harvester with much higher limits
"""

import subprocess
import os
import sys

def scale_up_podcast_harvesting():
    """Scale up podcast harvesting with much higher limits"""
    print("🚀 Scaling Up Podcast Harvester")
    print("=" * 50)
    
    print("📊 Current limits:")
    print("- Spotify: 15 episodes")
    print("- Apple Podcasts: 20 episodes") 
    print("- Google Podcasts: 15 episodes")
    print("- Total: ~50 episodes")
    
    print()
    print("🎯 New scaled-up limits:")
    print("- Spotify: 500 episodes")
    print("- Apple Podcasts: 500 episodes")
    print("- Google Podcasts: 500 episodes") 
    print("- Total: ~1,500 episodes")
    
    print()
    print("📈 Expected results:")
    print("- Current: 56 insights from 310 episodes (18% success rate)")
    print("- Scaled up: ~270 insights from 1,500 episodes")
    print("- New total: ~326 podcast insights")
    
    print()
    print("🔧 Modifications needed:")
    print("1. Increase max_results from 15-20 to 500 per platform")
    print("2. Add more search terms for broader coverage")
    print("3. Process more episodes per show")
    print("4. Apply same OpenAI filtering")
    
    print()
    print("🚀 Ready to scale up?")
    print("This will:")
    print("- Process 30x more episodes")
    print("- Generate ~5x more insights")
    print("- Take longer to run but get real results")
    
    return True

def run_scaled_up_harvest():
    """Run the scaled up podcast harvesting"""
    print("🎧 Running scaled up podcast harvest...")
    
    # Create a modified version of the harvester with higher limits
    modified_harvester = """
#!/usr/bin/env python3
# Modified podcast harvester with higher limits

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from harvest_podcast_platforms import PodcastPlatformHarvester

def scale_up_harvest():
    harvester = PodcastPlatformHarvester()
    
    # Expanded search terms for broader coverage
    search_terms = [
        "business strategy", "startup advice", "entrepreneur tips",
        "leadership", "management", "productivity", "marketing",
        "sales", "finance", "investing", "growth", "scaling",
        "innovation", "technology", "digital transformation",
        "customer success", "team building", "culture",
        "decision making", "problem solving", "risk management",
        "time management", "project management", "communication",
        "negotiation", "partnerships", "funding", "exit strategy",
        "remote work", "automation", "data analytics", "AI business",
        "ecommerce", "SaaS", "mobile apps", "web development",
        "cybersecurity", "compliance", "legal business", "tax strategy"
    ]
    
    print("🔍 Scaled up podcast harvesting...")
    
    # Use much higher limits
    spotify_episodes = harvester.harvest_spotify_podcasts(search_terms[:20], max_results=500)
    apple_episodes = harvester.harvest_apple_podcasts(search_terms[:20], max_results=500)
    google_episodes = harvester.harvest_google_podcasts(search_terms[:20], max_results=500)
    
    all_episodes = spotify_episodes + apple_episodes + google_episodes
    
    print(f"📊 Total episodes collected: {len(all_episodes)}")
    
    # Extract insights
    search_keywords = [
        "lesson learned", "best practice", "pro tip", "workaround", "gotcha",
        "trick", "pattern", "approach", "method", "technique", "strategy",
        "learned", "discovered", "found", "realized", "figured out",
        "worked", "failed", "succeeded", "mistake", "success", "failure",
        "always", "never", "because", "since", "therefore", "avoid",
        "prevent", "ensure", "make sure", "remember to", "experience",
        "insight", "wisdom", "advice", "the key is", "the secret is"
    ]
    
    insights = harvester.extract_insights_from_descriptions(all_episodes, search_keywords)
    
    print(f"✅ Found {len(insights)} insights")
    
    # Save to file
    import csv
    output_file = "data/scaled_up_podcast_insights.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        if insights:
            writer = csv.DictWriter(f, fieldnames=insights[0].keys())
            writer.writeheader()
            writer.writerows(insights)
    
    print(f"📁 Saved to {output_file}")
    return insights

if __name__ == "__main__":
    scale_up_harvest()
"""
    
    # Write the modified harvester
    with open("temp_scaled_up_podcasts.py", "w") as f:
        f.write(modified_harvester)
    
    # Run it
    try:
        result = subprocess.run([sys.executable, "temp_scaled_up_podcasts.py"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"❌ Error running scaled up harvest: {e}")
    finally:
        # Clean up
        if os.path.exists("temp_scaled_up_podcasts.py"):
            os.remove("temp_scaled_up_podcasts.py")

def main():
    """Main function"""
    print("🚀 Scale Up Podcast Harvester")
    print("=" * 50)
    
    # Show the plan
    scale_up_podcast_harvesting()
    
    print()
    response = input("Run the scaled up harvest? (y/n): ").strip().lower()
    
    if response == 'y':
        run_scaled_up_harvest()
    else:
        print("⏸️  Scaled up harvest cancelled")

if __name__ == "__main__":
    main()
