# Copy SQLite to PostgreSQL - FINAL FIX with timezone handling
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')
django.setup()

from django.db import connection
from django.conf import settings
from django.utils import timezone as django_timezone
from sonyApp.models import Channel, Video
import sqlite3
from datetime import datetime

print("🚀 Starting SQLite → PostgreSQL transfer...")

# Check if using PostgreSQL
db_engine = settings.DATABASES['default']['ENGINE']
if 'sqlite' in db_engine:
    print("❌ ERROR: Still using SQLite!")
    print("   Set DEBUG=False in your .env file")
    sys.exit(1)

print(f"✅ Target DB: {db_engine}")

# Connect to SQLite
sqlite_path = 'db.sqlite3'
if not os.path.exists(sqlite_path):
    print(f"❌ SQLite file not found: {sqlite_path}")
    sys.exit(1)

conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# Get counts
cursor.execute("SELECT COUNT(*) FROM sonyApp_channel")
channel_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM sonyApp_video")
video_count = cursor.fetchone()[0]

print(f"\n📊 SQLite Database:")
print(f"   Channels: {channel_count:,}")
print(f"   Videos: {video_count:,}")

input("\n⚠️  Press ENTER to clear PostgreSQL and copy data (or Ctrl+C to cancel)...")

# Clear PostgreSQL
print("\n🗑️  Clearing PostgreSQL...")
Video.objects.all().delete()
Channel.objects.all().delete()
print("   ✅ Cleared")

# Copy Channels FIRST and create mapping
print("\n📺 Copying channels...")
cursor.execute("SELECT id, channel_id, youtube_channel_id, name, description, thumbnail_url, subscriber_count, is_active, created_at, updated_at FROM sonyApp_channel")

channel_id_map = {}  # Old ID -> New Channel object
channels = []

for row in cursor.fetchall():
    old_id = row[0]
    
    # Parse timestamps
    created_at = row[8]
    updated_at = row[9]
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    
    # Make timezone-aware
    if created_at and not django_timezone.is_aware(created_at):
        created_at = django_timezone.make_aware(created_at)
    if updated_at and not django_timezone.is_aware(updated_at):
        updated_at = django_timezone.make_aware(updated_at)
    
    channel = Channel(
        id=old_id,
        channel_id=row[1],
        youtube_channel_id=row[2],
        name=row[3],
        description=row[4] or '',
        thumbnail_url=row[5] or '',
        subscriber_count=row[6] or 0,
        is_active=bool(row[7]),
        created_at=created_at,
        updated_at=updated_at,
    )
    channels.append(channel)
    channel_id_map[old_id] = channel

# Bulk create channels
Channel.objects.bulk_create(channels, batch_size=100)
print(f"   ✅ Copied {len(channels)} channels")

# Reload channels from DB to get proper IDs
print("\n🔄 Reloading channels from PostgreSQL...")
db_channels = {ch.id: ch for ch in Channel.objects.all()}

# Copy Videos with proper channel references
print("\n📹 Copying videos...")
cursor.execute("""
    SELECT id, channel_id, youtube_video_id, title, description, 
           thumbnail_url, duration, view_count, like_count, published_at, 
           is_short, is_active, created_at, updated_at 
    FROM sonyApp_video
""")

videos = []
total = 0
batch_size = 1000
skipped = 0

for row in cursor.fetchall():
    old_channel_id = row[1]
    
    # Skip if channel doesn't exist
    if old_channel_id not in db_channels:
        skipped += 1
        continue
    
    # Parse timestamps
    published_at = row[9]
    created_at = row[12]
    updated_at = row[13]
    
    # Convert to datetime if string
    if isinstance(published_at, str):
        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    
    # Make timezone-aware
    if published_at and not django_timezone.is_aware(published_at):
        published_at = django_timezone.make_aware(published_at)
    if created_at and not django_timezone.is_aware(created_at):
        created_at = django_timezone.make_aware(created_at)
    if updated_at and not django_timezone.is_aware(updated_at):
        updated_at = django_timezone.make_aware(updated_at)
    
    video = Video(
        id=row[0],
        channel=db_channels[old_channel_id],  # Use actual Channel object
        youtube_video_id=row[2],
        title=row[3],
        description=row[4] or '',
        thumbnail_url=row[5] or '',
        duration=row[6] or '',
        view_count=row[7] or 0,
        like_count=row[8] or 0,
        published_at=published_at,
        is_short=bool(row[10]),
        is_active=bool(row[11]),
        created_at=created_at,
        updated_at=updated_at,
    )
    videos.append(video)
    
    if len(videos) >= batch_size:
        Video.objects.bulk_create(videos, batch_size=batch_size)
        total += len(videos)
        print(f"   Progress: {total:,} videos...", end='\r', flush=True)
        videos = []

# Insert remaining
if videos:
    Video.objects.bulk_create(videos, batch_size=batch_size)
    total += len(videos)

print(f"\n   ✅ Copied {total:,} videos")
if skipped > 0:
    print(f"   ⚠️  Skipped {skipped} videos (missing channel)")

# Reset PostgreSQL sequences
print("\n🔧 Resetting sequences...")
try:
    with connection.cursor() as cur:
        cur.execute("SELECT setval('\"sonyApp_channel_id_seq\"', (SELECT COALESCE(MAX(id), 1) FROM \"sonyApp_channel\"))")
        cur.execute("SELECT setval('\"sonyApp_video_id_seq\"', (SELECT COALESCE(MAX(id), 1) FROM \"sonyApp_video\"))")
    print("   ✅ Sequences reset")
except Exception as e:
    print(f"   ⚠️  Could not reset sequences: {e}")

conn.close()

# Verify
final_channels = Channel.objects.count()
final_videos = Video.objects.count()

print("\n✅ DONE!")
print(f"   Channels: {final_channels:,}")
print(f"   Videos: {final_videos:,}")

if final_videos == video_count:
    print("\n🎉 All videos transferred successfully!")
else:
    print(f"\n⚠️  Expected {video_count:,} videos but got {final_videos:,}")