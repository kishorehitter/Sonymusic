"""
sonyApp/views.py
"""

import json
from datetime        import timedelta
from django.shortcuts               import render, get_object_or_404
from django.http                    import JsonResponse
from django.conf                    import settings
from django.core.cache              import cache
from django.utils                   import timezone
from django.db.models               import Q, Sum
from django.db.models.functions     import Coalesce
from django.core.paginator          import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http   import require_POST, require_http_methods
from django.views.decorators.csrf   import csrf_protect

from datetime import timedelta

from .models import Channel, Video

from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db import connection
from datetime import datetime
from io import StringIO
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def format_number(num):
    """Convert numbers to readable format - FIXED VERSION"""
    if not num:
        return '0'
    
    num = float(num)
    
    # Billions
    if num >= 1_000_000_000:
        val = num / 1_000_000_000
        if val >= 10:
            return f"{val:.0f}B"  # "10B", "15B"
        else:
            formatted = f"{val:.1f}B"
            return formatted.replace('.0B', 'B')  # "1.5B", not "1.0B"
    
    # Millions
    elif num >= 1_000_000:
        val = num / 1_000_000
        if val >= 10:
            return f"{val:.0f}M"  # "384M", "170M"
        else:
            formatted = f"{val:.1f}M"
            return formatted.replace('.0M', 'M')  # "38.4M", not "38.0M"
    
    # Thousands
    elif num >= 1_000:
        val = num / 1_000
        if val >= 10:
            return f"{val:.0f}K"  # "170K", "17K"
        else:
            formatted = f"{val:.1f}K"
            return formatted.replace('.0K', 'K')  # "1.5K", not "1.0K"
    
    else:
        return str(int(num))


# ═══════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════

def home(request):
    """
    Landing page — channels list + recent-video carousel.
    Only embeddable videos appear in carousel.
    Includes latest updates ticker (3 items, infinite scroll).
    """
    channels = Channel.objects.filter(is_active=True)

    # Carousel: last 30 days, embeddable only
    recent_videos = (
        Video.objects
        .filter(
            is_active=True,
            is_embeddable=True,
            published_at__gte=timezone.now() - timedelta(days=30),
        )
        .select_related('channel')
        .order_by('-published_at')[:10]
    )

    # ✅ Latest Updates Ticker: Only 3 most recent videos (last 24 hours)
    latest_updates = (
        Video.objects
        .filter(
            is_active=True,
            is_embeddable=True,
            published_at__gte=timezone.now() - timedelta(hours=24),
        )
        .select_related('channel')
        .order_by('-published_at')[:3]  # ✅ Only 3 items needed
    )

    # ── Statistics ──────────────────────────────────────
    total_artists = Channel.objects.filter(is_active=True).count()

    total_videos = Video.objects.filter(is_active=True).count()

    total_views = Video.objects.filter(is_active=True).aggregate(
        total=Coalesce(Sum('view_count'), 0)
    )['total']

    monthly_views = Video.objects.filter(
        is_active=True,
        published_at__gte=timezone.now() - timedelta(days=30),
    ).aggregate(
        total=Coalesce(Sum('view_count'), 0)
    )['total']

    total_languages = 15

    return render(request, 'sonyApp/webpage/home.html', {
        'channels':                channels,
        'recent_videos':           recent_videos,
        'latest_updates':          latest_updates,  # ✅ 3 items for ticker
        # raw
        'total_artists':           total_artists,
        'total_videos':            total_videos,
        'monthly_views':           monthly_views,
        'total_languages':         total_languages,
        # formatted
        'total_artists_formatted': format_number(total_artists),
        'total_videos_formatted':  format_number(total_videos),
        'monthly_views_formatted': format_number(monthly_views),
        'total_languages_formatted': f"{total_languages}+",
    })
# ═══════════════════════════════════════════════════════════════
# CHANNEL DETAIL
# ═══════════════════════════════════════════════════════════════

def channel_detail(request, channel_id):
    """
    Channel detail page — paginated video list.
    Non-embeddable videos are excluded.
    """
    channel = get_object_or_404(Channel, channel_id=channel_id)

    category    = request.GET.get('category', 'all')   # all | videos | shorts
    sort_by     = request.GET.get('sort', 'recent')     # recent | popular
    page_number = request.GET.get('page', 1)

    # Base queryset — embeddable only
    videos_qs = Video.objects.filter(
        channel=channel,
        is_active=True,
        is_embeddable=True,
    )

    # Counts for tabs (always from full embeddable set)
    total_videos = videos_qs.filter(is_short=False).count()
    total_shorts = videos_qs.filter(is_short=True).count()
    total_all = total_videos + total_shorts 

    # Category filter
    if category == 'videos':
        videos_qs = videos_qs.filter(is_short=False)
    elif category == 'shorts':
        videos_qs = videos_qs.filter(is_short=True)

    # Sort
    if sort_by == 'popular':
        videos_qs = videos_qs.order_by('-view_count', '-published_at')
    else:
        videos_qs = videos_qs.order_by('-published_at')

    # Paginate — 20 per page
    paginator = Paginator(videos_qs, 20)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'sonyApp/webpage/channel_detail.html', {
        'channel':       channel,
        'videos':        page_obj.object_list,
        'category':      category,
        'sort_by':       sort_by,
        'total_videos':  total_videos,
        'total_shorts':  total_shorts,
        'total_all':     total_all, 
        'page_obj':      page_obj,
    })


# ═══════════════════════════════════════════════════════════════
# VIDEO PLAYER
# ═══════════════════════════════════════════════════════════════

def video_player(request, channel_id, video_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)
    video = get_object_or_404(
        Video,
        youtube_video_id=video_id,
        channel=channel,
        is_active=True,
        is_embeddable=True,
    )

    is_short = video.is_short

    # ✅ SMART FILTERING (same type first)
    same_type = list(
        Video.objects
        .filter(channel=channel, is_active=True, is_embeddable=True, is_short=is_short)
        .exclude(youtube_video_id=video_id)
        .order_by('-published_at')[:20]
    )

    if len(same_type) < 20:
        existing_ids = {v.id for v in same_type}
        other_type = list(
            Video.objects
            .filter(channel=channel, is_active=True, is_embeddable=True, is_short=not is_short)
            .exclude(youtube_video_id=video_id)
            .exclude(id__in=existing_ids)
            .order_by('-published_at')[:20 - len(same_type)]
        )
        same_type.extend(other_type)

    seen = set()
    streaming = []
    for v in same_type:
        if v.id not in seen and v.youtube_video_id != video_id:
            seen.add(v.id)
            streaming.append(v)

    # ✅ Convert to JSON for JavaScript
    streaming_json = json.dumps([
        {
            'youtube_video_id': v.youtube_video_id,
            'title': v.title,
            'thumbnail_url': v.thumbnail_url,
            'is_short': v.is_short,
        }
        for v in streaming[:20]
    ])

    return render(request, 'sonyApp/webpage/video_player.html', {
        'channel': channel,
        'current_video': video,
        'streaming': streaming[:20],
        'streaming_json': streaming_json,  
        'current_is_short': is_short,
    })

# ═══════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def search_videos(request):
    """
    JSON search endpoint — returns videos, shorts, and channels.
    Only embeddable videos are returned.
    """
    query = request.GET.get('q', '').strip()

    def video_dict(video, is_short=False):
        return {
            'youtube_video_id': video.youtube_video_id,
            'title':            video.title,
            'channel_name':     video.channel.name,
            'channel_id':       video.channel.channel_id,
            'thumbnail':        video.thumbnail_url,
            'duration':         video.duration or ('0:60' if is_short else '0:00'),
            'views':            video.view_count or 0,
            'likes':            getattr(video, 'like_count', 0) or 0,
            'published':        video.published_at.strftime('%b %d, %Y') if video.published_at else '',
            'is_short':         is_short,
            'watch_url':        f"/channel/{video.channel.channel_id}/video/{video.youtube_video_id}/",
        }

    def channel_dict(ch):
        return {
            'channel_id':       ch.channel_id,
            'name':             ch.name,
            'description':      ch.description or '',
            'thumbnail':        ch.thumbnail_url or '',
            'subscriber_count': ch.subscriber_count or 0,
            'channel_url':      f"/channel/{ch.channel_id}/",
        }

    # ── Empty query → return recent content ──────────────────
    if not query:
        base = Video.objects.filter(is_active=True, is_embeddable=True)

        recent_videos = (
            base.filter(is_short=False)
            .select_related('channel')
            .order_by('-published_at')[:8]
        )
        recent_shorts = (
            base.filter(is_short=True)
            .select_related('channel')
            .order_by('-published_at')[:8]
        )
        return JsonResponse({
            'recent_videos': [video_dict(v, False) for v in recent_videos],
            'recent_shorts': [video_dict(v, True)  for v in recent_shorts],
        })

    # ── Keyword search ────────────────────────────────────────
    base_filter = Q(title__icontains=query) | Q(description__icontains=query) | Q(channel__name__icontains=query)
    embeddable  = dict(is_active=True, is_embeddable=True)

    videos = (
        Video.objects
        .filter(base_filter, is_short=False, **embeddable)
        .select_related('channel')
        .order_by('-published_at')[:15]
    )
    shorts = (
        Video.objects
        .filter(base_filter, is_short=True, **embeddable)
        .select_related('channel')
        .order_by('-published_at')[:15]
    )
    channels = (
        Channel.objects
        .filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True,
        )
        .order_by('-subscriber_count')[:5]
    )

    return JsonResponse({
        'videos':        [video_dict(v, False) for v in videos],
        'shorts':        [video_dict(v, True)  for v in shorts],
        'channels':      [channel_dict(c)       for c in channels],
        'total_results': videos.count() + shorts.count() + channels.count(),
    })


# ═══════════════════════════════════════════════════════════════
# CHANNELS DROPDOWN API  (used by navbar)
# ═══════════════════════════════════════════════════════════════

def channels_dropdown_api(request):
    """
    Returns all active channels for the navbar dropdown.
    """
    channels = Channel.objects.filter(is_active=True).order_by('name')

    return JsonResponse({
        'channels': [
            {
                'channel_id':         ch.channel_id,
                'youtube_channel_id': ch.youtube_channel_id,
                'name':               ch.name,
                'thumbnail_url':      ch.thumbnail_url,
                'subscriber_count':   ch.subscriber_count,
                'youtube_url':        f"https://www.youtube.com/channel/{ch.youtube_channel_id}",
                'handle':             getattr(ch, 'handle', ''),
                'description':        ch.description or '',
                'banner_url':         getattr(ch, 'banner_url', ''),
                'video_count':        Video.objects.filter(channel=ch, is_active=True).count(),
            }
            for ch in channels
        ],
        'total': channels.count(),
    })


# ═══════════════════════════════════════════════════════════════
# CHANNEL PREVIEW API  (modal popup)
# ═══════════════════════════════════════════════════════════════

def channel_preview_api(request, channel_id):
    """
    Returns channel details + recent videos for the subscribe modal.
    Uses local DB only — no YouTube API call (saves quota).
    """
    try:
        channel = get_object_or_404(Channel, channel_id=channel_id)

        recent_videos = (
            Video.objects
            .filter(channel=channel, is_active=True, is_embeddable=True)
            .order_by('-published_at')[:6]
        )

        return JsonResponse({
            'success': True,
            'channel': {
                'channel_id':         channel.channel_id,
                'youtube_channel_id': channel.youtube_channel_id,
                'name':               channel.name,
                'description':        channel.description or '',
                'thumbnail':          channel.thumbnail_url or '',
                'subscriber_count':   channel.subscriber_count or 0,
                'video_count':        Video.objects.filter(channel=channel, is_active=True).count(),
                'youtube_url':        f"https://www.youtube.com/channel/{channel.youtube_channel_id}",
                'handle':             getattr(channel, 'handle', ''),
            },
            'videos': [
                {
                    'video_id':    v.youtube_video_id,
                    'title':       v.title,
                    'thumbnail':   v.thumbnail_url,
                    'published_at': v.published_at.strftime('%b %d, %Y') if v.published_at else '',
                    'watch_url':   f"/channel/{channel.channel_id}/video/{v.youtube_video_id}/",
                }
                for v in recent_videos
            ],
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════
# FLAG NON-EMBEDDABLE  (called by video player JS on error 101/150)
# ═══════════════════════════════════════════════════════════════

@require_POST
@csrf_protect
def flag_unembeddable(request):
    """
    Sets Video.is_embeddable=False when YouTube blocks embedding.
    The video is then hidden from all listings automatically.
    """
    try:
        data     = json.loads(request.body)
        video_id = data.get('youtube_video_id', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'invalid body'}, status=400)

    if not video_id:
        return JsonResponse({'error': 'missing youtube_video_id'}, status=400)

    updated = Video.objects.filter(youtube_video_id=video_id).update(is_embeddable=False)

    return JsonResponse({
        'flagged':          updated > 0,
        'youtube_video_id': video_id,
    })


# ═══════════════════════════════════════════════════════════════
# INTERNAL CACHE HELPER  (used by management commands / tasks)
# ═══════════════════════════════════════════════════════════════

def get_channel_videos(channel):
    """
    Returns videos for a channel from cache, falling back to DB.
    Only returns active + embeddable videos.
    """
    cache_key = f'videos_{channel.channel_id}'
    videos    = cache.get(cache_key)

    if videos is None:
        videos = list(
            Video.objects
            .filter(channel=channel, is_active=True, is_embeddable=True)
            .order_by('-published_at')
        )
        cache.set(cache_key, videos, 3600)

    return videos

@csrf_exempt
@require_http_methods(["GET", "POST"])
def auto_fetch_videos(request):
    SECRET_TOKEN = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        start_time = datetime.now()
        out = StringIO()
        
        # ✅ Fetch only last 10 videos per channel
        call_command('fetch_youtube_videos', '--recent', '10', stdout=out)
        
        return JsonResponse({
            'success': True,
            'message': 'Fetch completed - last 10 videos per channel',
            'timestamp': start_time.isoformat(),
            'output': out.getvalue()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ────────────────────────────────────────────────────────────────
#  Health Check (Keep Alive)
# ────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check to keep Render awake.
    
    URL: https://your-app.onrender.com/api/health/
    """
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'videos': Video.objects.count(),
            'channels': Channel.objects.count(),
            'active_videos': Video.objects.filter(is_active=True).count(),
            'embeddable_videos': Video.objects.filter(is_embeddable=True).count()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=503)


# ────────────────────────────────────────────────────────────────
# full fetch all channel videos
# ────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["GET", "POST"])
def fetch_all_videos(request):
    SECRET_TOKEN = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        out = StringIO()
        
        # Fetch ALL videos for ALL channels
        call_command('fetch_youtube_videos', '--max-videos', '999999', stdout=out)
        
        return JsonResponse({
            'success': True,
            'message': 'Fetched all videos for all channels',
            'output': out.getvalue()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


  # ────────────────────────────────────────────────────────────────
#  fetch by channel videos
# ────────────────────────────────────────────────────────────────
  

@csrf_exempt
@require_http_methods(["GET", "POST"])
def fetch_all_channel_videos(request):
    SECRET_TOKEN = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    channel_id = request.GET.get('channel')
    
    if not channel_id:
        return JsonResponse({'error': 'channel parameter required'}, status=400)
    
    try:
        out = StringIO()
        
        # Fetch ALL videos for this specific channel
        call_command(
            'fetch_youtube_videos',
            '--channel', channel_id,
            '--max-videos', '999999',  # ALL videos
            stdout=out
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Fetched all videos for channel {channel_id}',
            'output': out.getvalue()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)