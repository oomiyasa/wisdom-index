#!/usr/bin/env python3
"""
Data cleanup and organization script for Wisdom Index
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_data_files():
    """Organize data files into subdirectories by type"""
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ Data directory not found")
        return
    
    # Create subdirectories
    subdirs = {
        "raw": data_dir / "raw",
        "filtered": data_dir / "filtered", 
        "wisdom": data_dir / "wisdom",
        "archive": data_dir / "archive"
    }
    
    for subdir in subdirs.values():
        subdir.mkdir(exist_ok=True)
    
    # Move files to appropriate directories
    moved_count = 0
    
    for file_path in data_dir.glob("*.csv"):
        if file_path.is_file():
            filename = file_path.name
            
            # Determine category based on filename
            if "wisdom_index" in filename or "wisdom" in filename:
                dest_dir = subdirs["wisdom"]
            elif "quality_filtered" in filename or "filtered" in filename:
                dest_dir = subdirs["filtered"]
            elif "test_" in filename or "debug_" in filename:
                dest_dir = subdirs["archive"]
            else:
                dest_dir = subdirs["raw"]
            
            # Move file
            dest_path = dest_dir / filename
            if dest_path.exists():
                # Add timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = filename.rsplit(".", 1)
                new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                dest_path = dest_dir / new_filename
            
            shutil.move(str(file_path), str(dest_path))
            moved_count += 1
            print(f"📁 Moved {filename} → {dest_dir.name}/")
    
    print(f"\n✅ Organized {moved_count} files into subdirectories")
    
    # Show directory structure
    print("\n📂 Current data structure:")
    for subdir_name, subdir_path in subdirs.items():
        count = len(list(subdir_path.glob("*.csv")))
        print(f"   {subdir_name}/: {count} files")

def cleanup_old_files(days_old=7):
    """Remove files older than specified days"""
    data_dir = Path("data")
    if not data_dir.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    removed_count = 0
    
    for file_path in data_dir.rglob("*.csv"):
        if file_path.is_file():
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                removed_count += 1
                print(f"🗑️  Removed old file: {file_path}")
    
    if removed_count > 0:
        print(f"\n✅ Removed {removed_count} old files")
    else:
        print(f"\n✅ No files older than {days_old} days found")

def show_data_summary():
    """Show summary of data files"""
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ Data directory not found")
        return
    
    print("📊 Data Summary:")
    print("=" * 50)
    
    total_files = 0
    total_size = 0
    
    for file_path in data_dir.rglob("*.csv"):
        if file_path.is_file():
            total_files += 1
            total_size += file_path.stat().st_size
            
            # Show file info
            size_mb = file_path.stat().st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"   {file_path.name:<40} {size_mb:>6.1f}MB  {modified}")
    
    total_size_mb = total_size / (1024 * 1024)
    print("=" * 50)
    print(f"   Total: {total_files} files, {total_size_mb:.1f}MB")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Data cleanup and organization")
    parser.add_argument("--organize", action="store_true", help="Organize files into subdirectories")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Remove files older than DAYS")
    parser.add_argument("--summary", action="store_true", help="Show data summary")
    
    args = parser.parse_args()
    
    if args.organize:
        organize_data_files()
    elif args.cleanup:
        cleanup_old_files(args.cleanup)
    elif args.summary:
        show_data_summary()
    else:
        # Default: show summary
        show_data_summary()
