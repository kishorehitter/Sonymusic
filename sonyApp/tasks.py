from background_task import background
from django.conf import settings
from django.utils import timezone
from .models import Channel, Video
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@background(schedule=60)  # Run every 60 seconds (1 minute) - for testing
def sync_recent_videos():
    """
    Background task to automatically fetch recent videos from all channels
    This runs automatically without any manual intervention!
    """
    logger.info("🎬 Starting automatic video sync...")
    
    # Get YouTube API key
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        logger.error("❌ YOUTUBE_API_KEY not set!")
        return
    
    # Build YouTube API client
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Get all active channels
    channels = Channel.objects.filter(is_active=True)
    
    if not channels.exists():
        logger.warning("⚠️ No active channels found")
        return
    
    total_new = 0
    total_updated = 0
    
    for channel in channels:
        try:
            logger.info(f"📺 Syncing: {channel.name}")
            
            # Fetch only videos from last 24 hours
            new_count, updated_count = fetch_recent_channel_videos(
                youtube, 
                channel,
                hours=24,  # Last 24 hours
                max_videos=50  # Max 50 recent videos
            )
            
            total_new += new_count
            total_updated += updated_count
            
            logger.info(f"   ✅ {channel.name}: {new_count} new, {updated_count} updated")
            
        except Exception as e:
            logger.error(f"   ❌ Error syncing {channel.name}: {e}")
    
    logger.info(f"✅ Sync complete! Total: {total_new} new, {total_updated} updated")
    
    # Schedule next run (1 hour from now)
    sync_recent_videos(schedule=3600)  # 3600 seconds = 1 hour


def fetch_recent_channel_videos(youtube, channel, hours=24, max_videos=50):
    """
    Fetch recent videos from a channel (last N hours)
    """
    new_videos = 0
    updated_videos = 0
    
    try:
        # Get channel info
        channel_response = youtube.channels().list(
            part='contentDetails,statistics',
            id=channel.youtube_channel_id
        ).execute()
        
        if not channel_response['items']:
            return new_videos, updated_videos
        
        # Update subscriber count
        stats = channel_response['items'][0].get('statistics', {})
        channel.subscriber_count = int(stats.get('subscriberCount', 0))
        channel.save()
        
        # Get uploads playlist
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Calculate cutoff time (videos from last N hours)
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Fetch recent videos
        playlist_response = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=max_videos
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_response['items']]
        
        if not video_ids:
            return new_videos, updated_videos
        
        # Get video details
        videos_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=','.join(video_ids)
        ).execute()
        
        # Process each video
        for video_data in videos_response['items']:
            # Check if video is recent
            published_at_str = video_data['snippet']['publishedAt']
            published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            
            # Only process videos published after cutoff
            if published_at < cutoff_time:
                continue
            
            # Save video
            created = save_video(channel, video_data)
            
            if created:
                new_videos += 1
                logger.info(f"      🆕 New: {video_data['snippet']['title'][:50]}...")
            else:
                updated_videos += 1
        
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
    
    return new_videos, updated_videos


def save_video(channel, video_data):
    """
    Save or update video in database
    """
    video_id = video_data['id']
    snippet = video_data['snippet']
    content_details = video_data['contentDetails']
    statistics = video_data.get('statistics', {})
    
    # Parse duration
    duration_iso = content_details.get('duration', 'PT0S')
    try:
        duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        secs = duration_seconds % 60
        
        if hours > 0:
            duration_formatted = f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            duration_formatted = f"{minutes}:{secs:02d}"
    except:
        duration_formatted = '0:00'
    
    # Parse published date
    published_at_str = snippet['publishedAt']
    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
    
    # Get best thumbnail
    thumbnails = snippet.get('thumbnails', {})
    thumbnail_url = (
        thumbnails.get('maxres', {}).get('url') or
        thumbnails.get('high', {}).get('url') or
        thumbnails.get('medium', {}).get('url') or
        thumbnails.get('default', {}).get('url', '')
    )
    
    # Create or update
    video, created = Video.objects.update_or_create(
        youtube_video_id=video_id,
        defaults={
            'channel': channel,
            'title': snippet.get('title', 'Untitled'),
            'description': snippet.get('description', ''),
            'thumbnail_url': thumbnail_url,
            'duration': duration_formatted,
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'published_at': published_at,
            'is_active': True,
        }
    )
    
    return created

