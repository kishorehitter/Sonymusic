"""
sonyApp/views.py
"""

import json
from datetime import timedelta
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_protect

from django.core.mail import send_mail

from datetime import timedelta

from .models import Channel, Video

from collections import Counter
import re

from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db import connection
from datetime import datetime
from io import StringIO
import logging

from django.urls import reverse

from django.views.decorators.cache import cache_page

# API endpoint for AJAX updates (called every 5 minutes by your JavaScript)
from django.http import JsonResponse
from django.views.decorators.http import require_GET

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


# def get_recent_artists_simple(limit=15):
#     """
#     Count artists - ONLY exact matches, no dangerous part searches
#     """
#     cache_key = f'recent_artists_exact_{limit}'
#     cached = cache.get(cache_key)
#     if cached:
#         return cached
    
#     ninety_days_ago = timezone.now() - timedelta(days=90)
    
#     # 🎵 CURATED LIST OF REAL MUSIC ARTISTS
#     REAL_ARTISTS = [
#         # Music Directors / Composers
#         'A.R. Rahman', 'Anirudh Ravichander', 'Yuvan Shankar Raja', 'Ilaiyaraaja',
#         'Harris Jayaraj', 'G.V. Prakash', 'D. Imman', 'Santhosh Narayanan',
#         'Sean Roldan', 'Hiphop Tamizha', 'Devi Sri Prasad', 'M.M. Keeravani',
#         'Thaman S', 'Pritam', 'Vishal Dadlani', 'Shekhar Ravjiani',
#         'Sam C.S.', 'Leon James', 'Siddhu Kumar', 'Justin Prabhakaran',
#         'Ron Ethan Yohann', 'Jakes Bejoy', 'Sushin Shyam', 'Dharan Kumar',
        
#         # Playback Singers - Male
#         'S.P. Balasubrahmanyam', 'K.J. Yesudas', 'Sid Sriram', 'Benny Dayal',
#         'Haricharan', 'Vijay Yesudas', 'Sathyaprakash', 'Pradeep Kumar',
#         'Armaan Malik', 'Arijit Singh', 'Mohit Chauhan', 'Javed Ali',
#         'Sonu Nigam', 'Shankar Mahadevan', 'Udit Narayan', 'Karthik',
#         'Rahul Nambiar', 'Ranjith', 'Vineeth Sreenivasan', 'Anand Aravindakshan',
#         'Shenbagaraj', 'Narayanan',
        
#         # Playback Singers - Female
#         'Shreya Ghoshal', 'Chinmayi', 'Jonita Gandhi', 'Neha Kakkar',
#         'Sunidhi Chauhan', 'K.S. Chithra', 'Sadhana Sargam', 'Alka Yagnik',
#         'Anuradha Sriram', 'Swetha Mohan', 'Madhushree', 'Bombay Jayashri',
#         'Vaikom Vijayalakshmi', 'Sithara', 'Shweta Mohan',
        
#         # Independent Artists / Bands
#         'Sivaangi Krishnakumar', 'Dhee', 'OfRo', 'The Indian Choral Ensemble',
#         'Agam', 'Thaikkudam Bridge', 'Avial', 'Masala Coffee',
#     ]
    
#     artist_data = []
    
#     for artist in REAL_ARTISTS:
#         # ONLY search for exact artist name - NO PART SEARCH
#         video_count = Video.objects.filter(
#             Q(title__icontains=artist) | Q(description__icontains=artist),
#             published_at__gte=ninety_days_ago,
#             is_active=True,
#             is_embeddable=True
#         ).distinct().count()
        
#         # Only include if count > 0
#         if video_count > 0:
#             # Get dates
#             videos = Video.objects.filter(
#                 Q(title__icontains=artist) | Q(description__icontains=artist),
#                 published_at__gte=ninety_days_ago,
#                 is_active=True,
#                 is_embeddable=True
#             ).order_by('-published_at').values_list('published_at', flat=True)[:50]
            
#             dates = [v.strftime('%b %d, %Y') for v in videos]
            
#             artist_data.append({
#                 'name': artist,
#                 'count': video_count,
#                 'dates': dates,
#                 'tooltip': (
#                     f"🎤 {artist}\n"
#                     f"📊 Total: {video_count} videos\n"
#                     f"📅 All dates:\n"
#                     f"{' • '.join(dates[:15])}{' …' if len(dates) > 15 else ''}\n"
#                     f"⏱️ {ninety_days_ago.strftime('%b %d')} – {timezone.now().strftime('%b %d, %Y')}"
#                 )
#             })
    
#     # Sort and limit
#     artist_data.sort(key=lambda x: x['count'], reverse=True)
#     top_artists = artist_data[:limit]
    
#     cache.set(cache_key, top_artists, 3600)
#     return top_artists

# ═══════════════════════════════════════════════════════════════
# ARTISTS PAGE  — optimized: 1 DB query instead of ~70
# ═══════════════════════════════════════════════════════════════

def artists_page(request):
    """
    Full artists list page.
    Uses a SINGLE DB query with Django ORM filtering + Python counting.
    Cached 1 hour.

    Strategy:
    - Fetch ALL matching videos in last 90 days in ONE query
    - Group/count in Python — much faster than 70 separate queries
    """
    cache_key = 'artists_page_data'
    cached = cache.get(cache_key)
    if cached:
        return render(request, 'sonyApp/webpage/artists.html', {'artists': cached})

    ninety_days_ago = timezone.now() - timedelta(days=90)

    REAL_ARTISTS = [
        # Music Directors / Composers
        'A.R. Rahman', 'Anirudh Ravichander', 'Yuvan Shankar Raja', 'Ilaiyaraaja',
        'Harris Jayaraj', 'G.V. Prakash', 'D. Imman', 'Santhosh Narayanan',
        'Sean Roldan', 'Hiphop Tamizha', 'Devi Sri Prasad', 'M.M. Keeravani',
        'Thaman S', 'Pritam', 'Vishal Dadlani', 'Shekhar Ravjiani',
        'Sam C.S.', 'Leon James', 'Siddhu Kumar', 'Justin Prabhakaran',
        'Ron Ethan Yohann', 'Jakes Bejoy', 'Sushin Shyam', 'Dharan Kumar',
        # Playback Singers - Male
        'S.P. Balasubrahmanyam', 'K.J. Yesudas', 'Sid Sriram', 'Benny Dayal',
        'Haricharan', 'Vijay Yesudas', 'Sathyaprakash', 'Pradeep Kumar',
        'Armaan Malik', 'Arijit Singh', 'Mohit Chauhan', 'Javed Ali',
        'Sonu Nigam', 'Shankar Mahadevan', 'Udit Narayan', 'Karthik',
        'Rahul Nambiar', 'Ranjith', 'Vineeth Sreenivasan', 'Anand Aravindakshan',
        'Shenbagaraj', 'Narayanan',
        # Playback Singers - Female
        'Shreya Ghoshal', 'Chinmayi', 'Jonita Gandhi', 'Neha Kakkar',
        'Sunidhi Chauhan', 'K.S. Chithra', 'Sadhana Sargam', 'Alka Yagnik',
        'Anuradha Sriram', 'Swetha Mohan', 'Madhushree', 'Bombay Jayashri',
        'Vaikom Vijayalakshmi', 'Sithara', 'Shweta Mohan',
        # Independent Artists / Bands
        'Sivaangi Krishnakumar', 'Dhee', 'OfRo', 'The Indian Choral Ensemble',
        'Agam', 'Thaikkudam Bridge', 'Avial', 'Masala Coffee',
    ]

    # ── Step 1: Build one big OR filter for ALL artists ──────────────────
    # One single DB query fetches all relevant video titles + descriptions
    combined_filter = Q()
    for artist in REAL_ARTISTS:
        combined_filter |= Q(title__icontains=artist) | Q(description__icontains=artist)

    # Fetch only the fields we need — no select_related required
    video_texts = list(
        Video.objects
        .filter(
            combined_filter,
            published_at__gte=ninety_days_ago,
            is_active=True,
            is_embeddable=True,
        )
        .values('title', 'description')   # only 2 fields — fast
    )

    # ── Step 2: Count in Python ───────────────────────────────────────────
    artist_data = []
    for artist in REAL_ARTISTS:
        artist_lower = artist.lower()
        count = sum(
            1 for v in video_texts
            if artist_lower in (v['title'] or '').lower()
            or artist_lower in (v['description'] or '').lower()
        )
        if count > 0:
            artist_data.append({'name': artist, 'count': count})

    # Sort descending
    artist_data.sort(key=lambda x: x['count'], reverse=True)

    # Add bar percentage relative to top artist
    max_count = artist_data[0]['count'] if artist_data else 1
    for a in artist_data:
        a['bar_pct'] = round((a['count'] / max_count) * 100)

    cache.set(cache_key, artist_data, 3600)  # cache 1 hour

    return render(request, 'sonyApp/webpage/artists.html', {
        'artists': artist_data,
    })
# ═══════════════════════════════════════════════════════════════
# ARTIST VIDEOS PAGE  — all videos for a specific artist
# ═══════════════════════════════════════════════════════════════

def artist_videos(request):
    """
    Shows all videos matching the artist name in title or description.
    URL: /artists/videos/?artist=Arijit+Singh
    """
    artist_name = request.GET.get('artist', '').strip()

    if not artist_name:
        return redirect('artists_page')

    ninety_days_ago = timezone.now() - timedelta(days=90)

    videos = (
        Video.objects
        .filter(
            Q(title__icontains=artist_name) | Q(description__icontains=artist_name),
            published_at__gte=ninety_days_ago,
            is_active=True,
            is_embeddable=True,
            channel__is_active=True,
        )
        .select_related('channel')
        .order_by('-published_at')
    )

    return render(request, 'sonyApp/webpage/artist_videos.html', {
        'artist_name':  artist_name,
        'videos':       videos,
        'total_count':  videos.count(),
    })

# ═══════════════════════════════════════════════════════════════
# GROWTH ANALYTICS  (3-section, 6h snapshot based)
# ═══════════════════════════════════════════════════════════════

def get_growth_sections():
    """
    Return videos for all 3 growth sections.

    Section 1 — Hot & New   : 0h  < age < 24h   | ranked by 6h delta
    Section 2 — Daily Growth: 24h ≤ age < 168h  | ranked by 24h rolling delta
    Section 3 — Weekly Growth:168h ≤ age < 720h | ranked by 168h rolling delta

    Results cached for 30 minutes (cache is busted on each cron run via
    cache.delete('growth_sections') inside update_video_stats if desired).
    """
    cache_key = 'growth_sections_v2'
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.now()

    # ── candidate pool: videos published in last 30 days, active, not shorts ──
    thirty_days_ago = now - timedelta(hours=720)
    candidates = (
        Video.objects
        .filter(
            channel__is_active=True,
            is_active=True,
            is_embeddable=True,
            is_short=False,
            published_at__gte=thirty_days_ago,
            base_snapshot_timestamp__isnull=False,   # must have at least 1 snapshot
        )
        .select_related('channel')
    )

    hot_list    = []
    daily_list  = []
    weekly_list = []

    for video in candidates:
        if video.in_hot_and_new():
            growth = video.get_hot_growth()
            if growth > 0:
                video.growth_value = growth
                video.growth_label = video.get_growth_label(section='hot')
                hot_list.append(video)

        elif video.in_daily_growth():
            growth = video.get_daily_growth()
            if growth > 0:
                video.growth_value = growth
                video.growth_label = video.get_growth_label(section='daily')
                daily_list.append(video)

        elif video.in_weekly_growth():
            growth = video.get_weekly_growth()
            if growth > 0:
                video.growth_value = growth
                video.growth_label = video.get_growth_label(section='weekly')
                weekly_list.append(video)

    # Sort each section by highest absolute growth
   
    hot_list.sort(key=lambda v: v.growth_value, reverse=True)
    daily_list.sort(key=lambda v: v.growth_value, reverse=True)
    weekly_list.sort(key=lambda v: v.growth_value, reverse=True)

    result = {
        'hot_and_new':   hot_list,
        'daily_growth':  daily_list,
        'weekly_growth': weekly_list,
    }

    cache.set(cache_key, result, 1800)   # cache 30 minutes
    return result



# ═══════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════

def home(request):
    """Landing page."""
    channels = Channel.objects.filter(is_active=True)

    # ── Carousel: last 30 days ─────────────────────────────────────────────
    recent_videos = (
        Video.objects
        .filter(
            channel__is_active=True,
            is_active=True,
            is_embeddable=True,
            published_at__gte=timezone.now() - timedelta(days=30),
        )
        .select_related('channel')
        .order_by('-published_at')[:10]
    )

    # ── Statistics ─────────────────────────────────────────────────────────
    total_artists = Channel.objects.filter(is_active=True).count()

    total_videos = Video.objects.filter(
        channel__is_active=True, is_active=True
    ).count()

    monthly_views = Video.objects.filter(
        channel__is_active=True,
        is_active=True,
        published_at__gte=timezone.now() - timedelta(days=30),
    ).aggregate(total=Coalesce(Sum('view_count'), 0))['total']

    total_subscribers = Channel.objects.filter(
        is_active=True
    ).aggregate(total=Coalesce(Sum('subscriber_count'), 0))['total']

    return render(request, 'sonyApp/webpage/home.html', {
        'channels':      channels,
        'recent_videos': recent_videos,

        # ── stats ──
        'total_artists_formatted':     format_number(total_artists),
        'total_videos_formatted':      format_number(total_videos),
        'monthly_views_formatted':     format_number(monthly_views),
        'total_subscribers_formatted': format_number(total_subscribers),
    })

# ═══════════════════════════════════════════════════════════════
# GROWTH PAGE  (full top 10 per section)
# ═══════════════════════════════════════════════════════════════

def growth_page(request):
    """Dedicated growth analytics page — top 10 per section."""
    growth_data = get_growth_sections()
    return render(request, 'sonyApp/webpage/growth.html', {
        'hot_and_new':  growth_data['hot_and_new'],    # top 10
        'daily_growth': growth_data['daily_growth'],   # top 10
        'weekly_growth': growth_data['weekly_growth'], # top 10
    })

# ═══════════════════════════════════════════════════════════════
# TRENDING API  (AJAX — called every 30 min by JS)
# ═══════════════════════════════════════════════════════════════

@require_GET
def api_trending(request):
    """Returns all 3 growth sections as JSON for AJAX refresh."""
    growth_data = get_growth_sections()

    def serialise(video, section):
        return {
            'title':        video.title,
            'channel_name': video.channel.name,
            'thumbnail_url': video.thumbnail_url,
            'growth':       video.growth_value,
            'growth_label': video.growth_label,
            'url': reverse('video_player', args=[video.channel.channel_id, video.youtube_video_id]),
        }

    return JsonResponse({
        'hot_and_new':   [serialise(v, 'hot')    for v in growth_data['hot_and_new']],
        'daily_growth':  [serialise(v, 'daily')  for v in growth_data['daily_growth']],
        'weekly_growth': [serialise(v, 'weekly') for v in growth_data['weekly_growth']],
    })

@require_GET
def last_stats_time(request):
    last = cache.get('last_stats_update')
    return JsonResponse({'last_updated': last})


# ═══════════════════════════════════════════════════════════════
# CHANNEL DETAIL
# ═══════════════════════════════════════════════════════════════

def channel_detail(request, channel_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)

    category    = request.GET.get('category', 'all')
    sort_by     = request.GET.get('sort', 'recent')
    page_number = request.GET.get('page', 1)

    videos_qs = Video.objects.filter(
        channel=channel, is_active=True, is_embeddable=True,
    )

    total_videos = videos_qs.filter(is_short=False).count()
    total_shorts = videos_qs.filter(is_short=True).count()
    total_all    = total_videos + total_shorts

    if category == 'videos':
        videos_qs = videos_qs.filter(is_short=False)
    elif category == 'shorts':
        videos_qs = videos_qs.filter(is_short=True)

    if sort_by == 'popular':
        videos_qs = videos_qs.order_by('-view_count', '-published_at')
    else:
        videos_qs = videos_qs.order_by('-published_at')

    paginator = Paginator(videos_qs, 20)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'sonyApp/webpage/channel_detail.html', {
        'channel':      channel,
        'videos':       page_obj.object_list,
        'category':     category,
        'sort_by':      sort_by,
        'total_videos': total_videos,
        'total_shorts': total_shorts,
        'total_all':    total_all,
        'page_obj':     page_obj,
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

    # ── Same type ONLY — no filling with opposite type ────────────────────────
    streaming = list(
        Video.objects
        .filter(channel=channel, is_active=True, is_embeddable=True, is_short=is_short)
        .exclude(youtube_video_id=video_id)
        .order_by('-published_at')[:20]
    )

    # ── JSON for end-screen JS (same type only, excludes current video) ───────
    streaming_json = json.dumps([
        {
            'youtube_video_id': v.youtube_video_id,
            'title':            v.title,
            'thumbnail_url':    v.thumbnail_url,
            'is_short':         v.is_short,
        }
        for v in streaming
    ])

    return render(request, 'sonyApp/webpage/video_player.html', {
        'channel':          channel,
        'current_video':    video,
        'streaming':        streaming,
        'streaming_json':   streaming_json,
        'current_is_short': is_short,
    })

# ═══════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def search_videos(request):
    """
    JSON search endpoint — returns videos, shorts, and channels.
    NOW WITH PREFIX-ONLY MATCHING - words must START with the query.
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

    # Split query into individual words
    search_words = query.split()
    
    # Build PREFIX-ONLY filter using regex with word boundaries
    # \y is word boundary in SQLite/PostgreSQL regex
    def build_prefix_filter(word):
        # Match word at start of string OR after space/punctuation
        return Q(title__iregex=r'(^|\s)' + word) | Q(channel__name__iregex=r'(^|\s)' + word)
    
    # If only one word
    if len(search_words) == 1:
        word = search_words[0]
        # Escape any regex special characters in the word
        import re
        escaped_word = re.escape(word)
        video_filter = build_prefix_filter(escaped_word)
        channel_filter = Q(name__iregex=r'(^|\s)' + escaped_word)
    
    # Multiple words - require ALL words to match as prefixes (AND)
    else:
        video_filter = Q()
        channel_filter = Q()
        
        for i, word in enumerate(search_words):
            import re
            escaped_word = re.escape(word)
            word_filter = build_prefix_filter(escaped_word)
            
            if i == 0:
                video_filter = word_filter
                channel_filter = Q(name__iregex=r'(^|\s)' + escaped_word)
            else:
                video_filter &= word_filter
                channel_filter &= Q(name__iregex=r'(^|\s)' + escaped_word)
    
    embeddable = dict(is_active=True, is_embeddable=True)

    # Get videos matching ALL words as prefixes
    videos = (
        Video.objects
        .filter(video_filter, is_short=False, **embeddable)
        .select_related('channel')
        .order_by('-published_at')[:15]
    )
    
    shorts = (
        Video.objects
        .filter(video_filter, is_short=True, **embeddable)
        .select_related('channel')
        .order_by('-published_at')[:15]
    )
    
    channels = (
        Channel.objects
        .filter(channel_filter, is_active=True)
        .order_by('-subscriber_count')[:5]
    )

    videos_list   = [video_dict(v, False) for v in videos]
    shorts_list   = [video_dict(v, True)  for v in shorts]
    channels_list = [channel_dict(c)      for c in channels]

    return JsonResponse({
        'videos':        videos_list,
        'shorts':        shorts_list,
        'channels':      channels_list,
        'total_results': len(videos_list) + len(shorts_list) + len(channels_list),
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

import threading

@require_http_methods(["POST"])
def enquiry(request):
    try:
        data    = json.loads(request.body)
        name    = data.get('name', '').strip()
        email   = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        to      = data.get('to', 'smsunoffical@gmail.com').strip()

        if not all([name, email, message]):
            return JsonResponse({'success': False, 'error': 'Missing required fields.'})

        email_body = f"""
New enquiry from Sony Music website

Name:    {name}
Email:   {email}
Subject: {subject}

Message:
{message}

---
Sent via exclusive-music.onrender.com contact form
        """.strip()

        import resend

        def send():
            try:
                resend.api_key = settings.RESEND_API_KEY
                resend.Emails.send({
                    "from": "Sony Music <onboarding@resend.dev>",
                    "to": [to],
                    "subject": f"[Sony Music] {subject}",
                    "text": email_body,
                })
                logger.info(f"✅ Email sent to {to}")
            except Exception as e:
                logger.error(f"❌ Resend error: {type(e).__name__}: {e}")


        threading.Thread(target=send, daemon=True).start()

        # Respond immediately — don't wait for email
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ═══════════════════════════════════════════════════════════════
# CRON JOB ENDPOINTS
# ═══════════════════════════════════════════════════════════════

# ── CRON 2: Fetch latest 5 videos per channel — every 10 minutes ──────────
# URL: /api/auto-fetch/?token=YOUR_TOKEN

@csrf_exempt
@require_http_methods(["GET", "POST"])
def auto_fetch_videos(request):
    """Fetch the 5 most recent videos per channel. Run every 10 minutes."""
    SECRET_TOKEN   = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        start_time = datetime.now()
        out = StringIO()
        call_command('fetch_youtube_videos', '--recent', '5', stdout=out)
        return JsonResponse({
            'success':   True,
            'message':   'Fetched latest 5 videos per channel',
            'timestamp': start_time.isoformat(),
            'output':    out.getvalue(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ── CRON 3& 4: 6hours & Daily full stats update — ALL videos ever stored ──────────────
# URL: /api/update-stats-full/?token=YOUR_TOKEN

@csrf_exempt
@require_http_methods(["GET", "POST"])
def auto_update_stats(request):
    SECRET_TOKEN   = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        days = int(request.GET.get('days', 31))
    except ValueError:
        days = 31

    import threading
    def run():
        try:
            out = StringIO()
            call_command('update_video_stats', '--days', str(days), stdout=out)
            cache.delete('growth_sections_v2')
            cache.set('last_stats_update', datetime.now().isoformat(), 86400)
            logger.info(f"Stats update done: last {days} days")
        except Exception as e:
            logger.error(f"auto_update_stats error: {e}")

    threading.Thread(target=run, daemon=True).start()

    return JsonResponse({
        'success':   True,
        'message':   f'Stats update started for last {days} days',
        'timestamp': datetime.now().isoformat(),
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def auto_update_stats_full(request):
    SECRET_TOKEN   = settings.AUTO_SYNC_SECRET_TOKEN
    provided_token = request.GET.get('token')
    if SECRET_TOKEN and provided_token != SECRET_TOKEN:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    import threading
    def run():
        try:
            out = StringIO()
            call_command('update_video_stats', '--days', '36500', stdout=out)
            cache.delete('growth_sections_v2')
            cache.set('last_stats_update', datetime.now().isoformat(), 86400)
            logger.info("Full stats update complete")
        except Exception as e:
            logger.error(f"auto_update_stats_full error: {e}")

    threading.Thread(target=run, daemon=True).start()

    return JsonResponse({
        'success':   True,
        'message':   'Full stats update started in background',
        'timestamp': datetime.now().isoformat(),
    })

# ────────────────────────────────────────────────────────────────
#  Health Check (Keep Alive)
# ────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def health_check(request):
    """
    Lightweight keep-alive ping — zero DB queries.
    Just confirms the server process is awake.
    """
    return JsonResponse({'status': 'ok'})


# ────────────────────────────────────────────────────────────────
# full fetch all channel videos
# ────────────────────────────────────────────────────────────────

# @csrf_exempt
# @require_http_methods(["GET", "POST"])
# def fetch_all_videos(request):
#     SECRET_TOKEN = settings.AUTO_SYNC_SECRET_TOKEN
#     provided_token = request.GET.get('token')
    
#     if SECRET_TOKEN and provided_token != SECRET_TOKEN:
#         return JsonResponse({'error': 'Unauthorized'}, status=401)
    
#     try:
#         out = StringIO()
        
#         # Fetch ALL videos for ALL channels
#         call_command('fetch_youtube_videos', '--max-videos', '999999', stdout=out)
        
#         return JsonResponse({
#             'success': True,
#             'message': 'Fetched all videos for all channels',
#             'output': out.getvalue()
#         })
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)


  # ────────────────────────────────────────────────────────────────
#  fetch by channel videos
# ────────────────────────────────────────────────────────────────
  

# @csrf_exempt
# @require_http_methods(["GET", "POST"])
# def fetch_all_channel_videos(request):
#     SECRET_TOKEN = settings.AUTO_SYNC_SECRET_TOKEN
#     provided_token = request.GET.get('token')
    
#     if SECRET_TOKEN and provided_token != SECRET_TOKEN:
#         return JsonResponse({'error': 'Unauthorized'}, status=401)
    
#     channel_id = request.GET.get('channel')
    
#     if not channel_id:
#         return JsonResponse({'error': 'channel parameter required'}, status=400)
    
#     try:
#         out = StringIO()
        
#         # Fetch ALL videos for this specific channel
#         call_command(
#             'fetch_youtube_videos',
#             '--channel', channel_id,
#             '--max-videos', '999999',  # ALL videos
#             stdout=out
#         )
        
#         return JsonResponse({
#             'success': True,
#             'message': f'Fetched all videos for channel {channel_id}',
#             'output': out.getvalue()
#         })
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)