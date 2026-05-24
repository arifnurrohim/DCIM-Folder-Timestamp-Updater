#!/usr/bin/env python3
"""
Script to update folder modification timestamps based on EXIF creation dates
with optional backup functionality.
"""

import os
import sys
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("PIL/Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)

def get_user_choice() -> dict:
    """Interactive menu to get user preferences."""
    print("\n" + "=" * 60)
    print("📸 DCIM Folder Timestamp Updater")
    print("=" * 60)
    
    # Backup option
    print("\n💾 Backup Options:")
    print("  1. Create backup before making changes (Recommended)")
    print("  2. Skip backup (Faster, but no undo option)")
    print("  3. Preview only (Dry run - no changes)")
    
    while True:
        choice = input("\nSelect option (1/2/3): ").strip()
        if choice == '1':
            backup = True
            dry_run = False
            break
        elif choice == '2':
            print("\n⚠️  WARNING: Skipping backup means changes cannot be undone!")
            confirm = input("Are you sure? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                backup = False
                dry_run = False
                break
            else:
                print("Backup will be created for safety.")
                backup = True
                dry_run = False
                break
        elif choice == '3':
            backup = False
            dry_run = True
            print("\n🔍 DRY RUN MODE: No changes will be made")
            break
        else:
            print("❌ Invalid choice. Please select 1, 2, or 3.")
    
    # Custom path option
    print("\n📂 Folder Options:")
    print("  1. Use default path (/storage/emulated/0/DCIM)")
    print("  2. Enter custom path")
    
    while True:
        path_choice = input("\nSelect option (1/2): ").strip()
        if path_choice == '1':
            dcim_path = Path("/storage/emulated/0/DCIM")
            break
        elif path_choice == '2':
            custom_path = input("Enter full path: ").strip()
            dcim_path = Path(custom_path)
            break
        else:
            print("❌ Invalid choice. Please select 1 or 2.")
    
    # Custom backup path (only if backup is enabled)
    backup_path = None
    if backup and not dry_run:
        print("\n💿 Backup Location:")
        print("  1. Use default (/storage/emulated/0/DCIM_BACKUP)")
        print("  2. Enter custom location")
        
        while True:
            backup_choice = input("\nSelect option (1/2): ").strip()
            if backup_choice == '1':
                backup_path = Path("/storage/emulated/0/DCIM_BACKUP")
                break
            elif backup_choice == '2':
                custom_backup = input("Enter backup path: ").strip()
                backup_path = Path(custom_backup)
                break
            else:
                print("❌ Invalid choice. Please select 1 or 2.")
    
    return {
        'backup': backup,
        'dry_run': dry_run,
        'dcim_path': dcim_path,
        'backup_path': backup_path
    }

def create_backup(source_path: Path, backup_path: Path) -> Tuple[bool, str]:
    """Create a backup of the DCIM folder before making changes."""
    try:
        print(f"\n📦 Creating backup...")
        print(f"   Source: {source_path}")
        print(f"   Backup: {backup_path}")
        
        # Check if backup already exists
        if backup_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_old = Path(f"{backup_path}_{timestamp}")
            print(f"   ⚠ Backup already exists, moving to: {backup_old}")
            shutil.move(str(backup_path), str(backup_old))
        
        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all contents
        total_items = 0
        for item in source_path.iterdir():
            if item.is_dir():
                dest = backup_path / item.name
                shutil.copytree(item, dest, symlinks=False, ignore_dangling_symlinks=True)
                total_items += 1
                print(f"   ✓ Backed up folder: {item.name}")
            elif item.is_file():
                shutil.copy2(item, backup_path)
                total_items += 1
        
        print(f"   ✅ Backup completed successfully! ({total_items} items)")
        return True, f"Backup created at {backup_path}"
        
    except Exception as e:
        error_msg = f"Backup failed: {e}"
        print(f"   ❌ {error_msg}")
        return False, error_msg

def get_exif_date(image_path: Path) -> Optional[datetime]:
    """Extract creation date from image EXIF data."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == 'DateTimeOriginal':
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
                elif tag_name == 'DateTimeDigitized':
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
                elif tag_name == 'DateTime':
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass
    return None

def find_oldest_exif_date(folder_path: Path, verbose: bool = False) -> Optional[datetime]:
    """Find the oldest EXIF creation date in all images within a folder."""
    oldest_date = None
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.dng', '.cr2', '.nef', '.tiff', '.bmp'}
    file_count = 0
    success_count = 0
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                file_count += 1
                file_path = Path(root) / file
                exif_date = get_exif_date(file_path)
                
                if exif_date:
                    success_count += 1
                    if oldest_date is None or exif_date < oldest_date:
                        oldest_date = exif_date
    
    if verbose and file_count > 0:
        print(f"      📸 Scanned {file_count} images, extracted {success_count} EXIF dates")
    
    return oldest_date

def update_folder_modification_time(folder_path: Path, timestamp: datetime, dry_run: bool = False) -> bool:
    """Update folder's last modification time."""
    try:
        mod_time = timestamp.timestamp()
        
        if dry_run:
            print(f"      [DRY RUN] Would update to: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        
        os.utime(folder_path, (mod_time, mod_time))
        
        # Verify the change
        new_mtime = os.path.getmtime(folder_path)
        if abs(new_mtime - mod_time) < 0.1:
            return True
        return False
    except Exception as e:
        print(f"      Error updating folder {folder_path}: {e}")
        return False

def process_dcim_folder(config: dict) -> bool:
    """Main function to process DCIM folder and its subfolders."""
    
    dcim_path = config['dcim_path']
    backup = config['backup']
    dry_run = config['dry_run']
    backup_path = config['backup_path']
    
    if not dcim_path.exists():
        print(f"❌ Error: Path {dcim_path} does not exist!")
        return False
    
    if not dcim_path.is_dir():
        print(f"❌ Error: {dcim_path} is not a directory!")
        return False
    
    print("\n" + "=" * 70)
    print("📸 Configuration Summary")
    print("=" * 70)
    print(f"Target folder: {dcim_path}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE MODE'}")
    print(f"Backup: {'Enabled' if backup and not dry_run else 'Disabled'}")
    if backup and not dry_run:
        print(f"Backup location: {backup_path}")
    
    # Create backup if requested
    if backup and not dry_run:
        backup_success, backup_msg = create_backup(dcim_path, backup_path)
        if not backup_success:
            print("\n❌ Backup failed. Aborting to prevent data loss.")
            return False
        print(backup_msg)
    elif dry_run:
        print("\n🔍 DRY RUN: Skipping backup (no changes will be made)")
    else:
        print("\n⚠️  Running without backup - changes cannot be undone!")
        confirm = input("Continue without backup? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Operation cancelled.")
            return False
    
    # Get all subfolders
    subfolders = [f for f in dcim_path.iterdir() if f.is_dir()]
    
    if not subfolders:
        print("\n⚠️ No subfolders found in DCIM directory")
        return True
    
    results = []
    
    print("\n📁 Processing folders...")
    print("-" * 70)
    
    for folder in sorted(subfolders):
        print(f"\n📂 Processing: {folder.name}")
        oldest_date = find_oldest_exif_date(folder, verbose=True)
        
        if oldest_date:
            formatted_date = oldest_date.strftime("%Y-%m-%d %H:%M:%S")
            current_mtime = datetime.fromtimestamp(os.path.getmtime(folder))
            current_formatted = current_mtime.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"   📅 Current modified: {current_formatted}")
            print(f"   📅 Oldest EXIF date: {formatted_date}")
            
            if update_folder_modification_time(folder, oldest_date, dry_run):
                if not dry_run:
                    new_mtime = datetime.fromtimestamp(os.path.getmtime(folder))
                    print(f"   ✅ Updated to: {new_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                results.append((folder.name, "✅ Success", formatted_date, current_formatted))
            else:
                print(f"   ❌ Failed to update")
                results.append((folder.name, "❌ Failed", formatted_date, current_formatted))
        else:
            print(f"   ⚠️  No EXIF dates found in any images")
            results.append((folder.name, "⚠️  No EXIF data", "N/A", "N/A"))
    
    # Process main DCIM folder
    print(f"\n📂 Processing: DCIM (main folder)")
    oldest_in_dcim = find_oldest_exif_date(dcim_path, verbose=True)
    if oldest_in_dcim:
        formatted_date = oldest_in_dcim.strftime("%Y-%m-%d %H:%M:%S")
        current_mtime = datetime.fromtimestamp(os.path.getmtime(dcim_path))
        current_formatted = current_mtime.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"   📅 Current modified: {current_formatted}")
        print(f"   📅 Oldest EXIF date: {formatted_date}")
        
        if update_folder_modification_time(dcim_path, oldest_in_dcim, dry_run):
            if not dry_run:
                new_mtime = datetime.fromtimestamp(os.path.getmtime(dcim_path))
                print(f"   ✅ Updated to: {new_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            results.append(("DCIM (main)", "✅ Success", formatted_date, current_formatted))
    else:
        print(f"   ⚠️  No EXIF dates found")
        results.append(("DCIM (main)", "⚠️  No EXIF data", "N/A", "N/A"))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"{'Folder':<25} {'Status':<15} {'Original Date':<20} {'New Date':<20}")
    print("-" * 80)
    for folder, status, new_date, old_date in results:
        if status == "✅ Success":
            print(f"{folder:<25} {status:<15} {old_date:<20} {new_date:<20}")
        else:
            print(f"{folder:<25} {status:<15} {old_date:<20} -")
    
    if backup and not dry_run:
        print(f"\n💾 Backup location: {backup_path}")
        print("⚠️  To restore: cp -r", backup_path, "*", dcim_path.parent)
    
    return True

def main():
    """Main entry point with interactive menu."""
    
    # Get user preferences
    config = get_user_choice()
    
    # Process the DCIM folder
    success = process_dcim_folder(config)
    
    if success:
        if config['dry_run']:
            print("\n✨ Dry run completed. No changes were made.")
            print("   Run again and select option 1 or 2 to apply changes.")
        else:
            print("\n✨ Operation completed successfully!")
    else:
        print("\n❌ Operation failed!")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()