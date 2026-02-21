"""
management/commands/fetch_youtube_videos.py

Fetches videos from YouTube channels with RELIABLE embeddability detection.

WHY noembed.com instead of YouTube oEmbed or status.embeddable?
  - YouTube Data API status.embeddable returns True even for restricted videos.
  - YouTube oEmbed (youtube.com/oembed) also returns 200 for restricted videos.
  - noembed.com actually tests embed availability:
      {"html": "<iframe...>"}  → embeddable
      {"error": "..."}        → blocked

Usage:
  python manage.py fetch_youtube_videos
  python manage.py fetch_youtube_videos --max-videos 999999
  python manage.py fetch_youtube_videos --update-existing
  python manage.py fetch_youtube_videos --channel my_channel_id
  python manage.py fetch_youtube_videos --days 7
  python manage.py fetch_youtube_videos --check-embeddable-only
"""

import isodate
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime           import datetime, timedelta

from django.core.management.base import BaseCommand
from django.conf                  import settings
from django.utils                 import timezone

from googleapiclient.discovery    import build
from googleapiclient.errors       import HttpError

from sonyApp.models import Channel, Video


# ── Shared HTTP session (keep-alive, reused across threads) ──────────────────
_session = requests.Session()
_session.headers.update({'User-Agent': 'Mozilla/5.0'})

# noembed.com returns {"error":"..."} for non-embeddable, {"html":"<iframe..."} for embeddable
NOEMBED_URL = "https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"


def check_embeddable(video_id: str) -> bool:
    """
    Returns True  → video CAN be embedded on third-party sites.
    Returns False → embedding is restricted by the video owner.

    Uses noembed.com which physically tests embed availability.
    YouTube's own oEmbed and status.embeddable API field both return
    'embeddable' even for videos that block third-party embedding.
    """
    try:
        url      = NOEMBED_URL.format(video_id=video_id)
        response = _session.get(url, timeout=5)

        if response.status_code != 200:
            return False

        data = response.json()

        # noembed explicitly returns {"error": "..."} when blocked
        if 'error' in data:
            return False

        # Must have an actual iframe html to be truly embeddable
        if data.get('html'):
            return True

        return False

    except (requests.RequestException, ValueError, KeyError):
        # On any failure → assume embeddable (JS player will catch it as fallback)
        return True


class Command(BaseCommand):
    help = 'Fetch YouTube channel videos with reliable embeddability detection via noembed.com'

    def add_arguments(self, parser):
        parser.add_argument('--channel',        type=str,  help='Specific channel_id to fetch')
        parser.add_argument('--max-videos',     type=int,  help='Max videos per channel (default 50)')
        parser.add_argument('--recent',         type=int,  help='Fetch N most recent videos')
        parser.add_argument('--days',           type=int,  help='Only videos from last N days')
        parser.add_argument('--since',          type=str,  help='Only videos since YYYY-MM-DD')
        parser.add_argument('--update-existing', action='store_true',
                            help='Re-fetch and update existing videos')
        parser.add_argument('--check-embeddable-only', action='store_true',
                            help='Only re-check embeddability for existing videos (fast, no quota)')

    def handle(self, *args, **options):

        # ── Special mode: just re-check embeddability ─────────────────────
        if options.get('check_embeddable_only'):
            self.recheck_all_embeddability()
            return

        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR('❌ YOUTUBE_API_KEY not configured in settings'))
            return

        youtube    = build('youtube', 'v3', developerKey=api_key)
        max_videos = options.get('recent') or options.get('max_videos') or 50

        # Date filter
        date_filter = None
        if options.get('days'):
            date_filter = timezone.now() - timedelta(days=options['days'])
            self.stdout.write(self.style.WARNING(f'📅 Filtering: last {options["days"]} days'))
        elif options.get('since'):
            try:
                date_filter = timezone.make_aware(
                    datetime.strptime(options['since'], '%Y-%m-%d')
                )
                self.stdout.write(self.style.WARNING(f'📅 Filtering: since {options["since"]}'))
            except ValueError:
                self.stdout.write(self.style.ERROR('❌ Invalid date format. Use YYYY-MM-DD'))
                return

        # Channels to process
        if options.get('channel'):
            channels = Channel.objects.filter(channel_id=options['channel'], is_active=True)
            if not channels.exists():
                self.stdout.write(self.style.ERROR(f'❌ Channel not found: {options["channel"]}'))
                return
        else:
            channels = Channel.objects.filter(is_active=True)

        if not channels.exists():
            self.stdout.write(self.style.ERROR('❌ No active channels found'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n🎬 Fetching videos for {channels.count()} channel(s)...\n'
        ))

        total_new = total_updated = total_skipped = total_blocked = 0

        for channel in channels:
            self.stdout.write(f'\n📺 {channel.name}')
            self.stdout.write(f'   YouTube ID: {channel.youtube_channel_id}')

            try:
                new, updated, skipped, blocked = self.fetch_channel_videos(
                    youtube, channel, max_videos, date_filter,
                    options.get('update_existing', False)
                )
                total_new     += new
                total_updated += updated
                total_skipped += skipped
                total_blocked += blocked

                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ New: {new} | Updated: {updated} | '
                    f'Skipped: {skipped} | 🚫 Blocked: {blocked}'
                ))

            except HttpError as e:
                self.stdout.write(self.style.ERROR(f'   ❌ YouTube API error: {e}'))
            except Exception as e:
                import traceback
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {e}'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done!\n'
            f'   New:        {total_new}\n'
            f'   Updated:    {total_updated}\n'
            f'   Skipped:    {total_skipped}\n'
            f'   🚫 Blocked: {total_blocked}\n'
        ))

    # ── Fetch all videos for one channel ─────────────────────────────────────
    def fetch_channel_videos(self, youtube, channel, max_videos,
                              date_filter=None, update_existing=False):
        new_count = updated_count = skipped_count = blocked_count = 0

        ch_resp = youtube.channels().list(
            part='contentDetails,statistics',
            id=channel.youtube_channel_id
        ).execute()

        if not ch_resp.get('items'):
            self.stdout.write(self.style.WARNING('   ⚠️  Channel not found on YouTube'))
            return new_count, updated_count, skipped_count, blocked_count

        stats = ch_resp['items'][0].get('statistics', {})
        channel.subscriber_count = int(stats.get('subscriberCount', 0))
        channel.save(update_fields=['subscriber_count'])
        self.stdout.write(f'   📊 Subscribers: {channel.subscriber_count:,}')

        uploads_id = ch_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        next_page  = None
        fetched    = 0

        while fetched < max_videos:
            batch = min(50, max_videos - fetched)

            pl_resp = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_id,
                maxResults=batch,
                pageToken=next_page,
            ).execute()

            video_ids = [i['contentDetails']['videoId'] for i in pl_resp.get('items', [])]
            if not video_ids:
                break

            vids_resp = youtube.videos().list(
                part='snippet,contentDetails,statistics,status',
                id=','.join(video_ids),
            ).execute()

            for vdata in vids_resp.get('items', []):
                fetched += 1
                vid = vdata['id']

                # Date filter
                if date_filter:
                    pub = datetime.fromisoformat(
                        vdata['snippet']['publishedAt'].replace('Z', '+00:00')
                    )
                    if pub < date_filter:
                        skipped_count += 1
                        continue

                # Skip existing unless --update-existing
                if not update_existing and Video.objects.filter(youtube_video_id=vid).exists():
                    skipped_count += 1
                    continue

                # ── Embeddability check via noembed.com ────────────────
                is_emb = check_embeddable(vid)
                if not is_emb:
                    blocked_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'   🚫 {vdata["snippet"].get("title","?")[:55]}'
                        )
                    )

                created = self.save_video(channel, vdata, is_emb)
                if created:
                    new_count += 1
                else:
                    updated_count += 1

                if (new_count + updated_count) % 10 == 0:
                    self.stdout.write(
                        f'   📹 {new_count + updated_count} processed...', ending='\r'
                    )
                    self.stdout.flush()

            next_page = pl_resp.get('nextPageToken')
            if not next_page:
                break

        return new_count, updated_count, skipped_count, blocked_count

    # ── Save / update one video ───────────────────────────────────────────────
    def save_video(self, channel, vdata, is_embeddable: bool) -> bool:
        vid_id  = vdata['id']
        snippet = vdata['snippet']
        details = vdata['contentDetails']
        stats   = vdata.get('statistics', {})

        duration_iso = details.get('duration', 'PT0S')
        try:
            total_secs   = int(isodate.parse_duration(duration_iso).total_seconds())
            duration_str = self.format_duration(total_secs)
        except Exception:
            total_secs   = 0
            duration_str = '0:00'

        is_short = 0 < total_secs <= 60

        pub_dt = datetime.fromisoformat(
            snippet['publishedAt'].replace('Z', '+00:00')
        )

        thumbs = snippet.get('thumbnails', {})
        thumb  = (
            thumbs.get('maxres', {}).get('url') or
            thumbs.get('high',   {}).get('url') or
            thumbs.get('medium', {}).get('url') or
            thumbs.get('default',{}).get('url', '')
        )

        _, created = Video.objects.update_or_create(
            youtube_video_id=vid_id,
            defaults={
                'channel':       channel,
                'title':         snippet.get('title', 'Untitled'),
                'description':   snippet.get('description', ''),
                'thumbnail_url': thumb,
                'duration':      duration_str,
                'view_count':    int(stats.get('viewCount', 0)),
                'like_count':    int(stats.get('likeCount', 0)),
                'published_at':  pub_dt,
                'is_active':     True,
                'is_short':      is_short,
                'is_embeddable': is_embeddable,
            }
        )
        return created

    # ── Re-check embeddability for ALL existing DB videos (parallel) ──────────
    def recheck_all_embeddability(self):
        """
        Parallel embeddability re-check using 30 threads.
        Does NOT use YouTube API quota — only calls noembed.com.

        Run with:  python manage.py fetch_youtube_videos --check-embeddable-only
        """
        THREADS = 30

        videos = list(
            Video.objects.filter(is_active=True)
            .values('id', 'youtube_video_id', 'title', 'is_embeddable')
        )
        total = len(videos)

        self.stdout.write(self.style.SUCCESS(
            f'\n🔍 Checking {total} videos with {THREADS} threads via noembed.com...\n'
        ))

        lock          = threading.Lock()
        processed     = [0]
        blocked_count = [0]
        to_block      = []   # ids that should be False
        to_unblock    = []   # ids that should be True

        def check_one(v):
            is_emb = check_embeddable(v['youtube_video_id'])

            with lock:
                processed[0] += 1

                if v['is_embeddable'] != is_emb:
                    if is_emb:
                        to_unblock.append(v['id'])
                    else:
                        to_block.append(v['id'])
                        blocked_count[0] += 1
                        self.stdout.write(
                            self.style.WARNING(f'   🚫 Blocked: {v["title"][:60]}')
                        )

                if processed[0] % 30 == 0 or processed[0] == total:
                    self.stdout.write(
                        f'   📹 {processed[0]}/{total}...', ending='\r'
                    )
                    self.stdout.flush()

        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            futures = [pool.submit(check_one, v) for v in videos]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    with lock:
                        self.stdout.write(self.style.ERROR(f'\n   ⚠️  Thread error: {e}'))

        self.stdout.write('')  # newline after \r

        # Bulk DB update — max 2 queries total
        if to_block:
            Video.objects.filter(id__in=to_block).update(is_embeddable=False)
        if to_unblock:
            Video.objects.filter(id__in=to_unblock).update(is_embeddable=True)

        changed = len(to_block) + len(to_unblock)
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done!\n'
            f'   Checked:    {processed[0]}\n'
            f'   Changed:    {changed}\n'
            f'   🚫 Blocked: {blocked_count[0]}\n'
        ))

    # ── Duration formatter ────────────────────────────────────────────────────
    def format_duration(self, seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"