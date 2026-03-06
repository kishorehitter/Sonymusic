# sonyApp/management/commands/update_video_stats.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sonyApp.models import Video, Channel
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update video statistics every 6 hours and store growth snapshots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Only update videos published in last N days (default: 30)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of videos per YouTube API batch (default: 50)'
        )
        parser.add_argument(
            '--channel',
            type=str,
            help='Update only a specific channel (channel_id)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting 6h video stats update...'))

        # ── Init YouTube API ─────────────────────────────────────────────────
        try:
            youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)
            self.stdout.write("✅ YouTube API initialised")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to initialise YouTube API: {e}'))
            return

        # ── Build queryset ───────────────────────────────────────────────────
        cutoff_date = timezone.now() - timedelta(days=options['days'])
        videos_qs = Video.objects.filter(
            channel__is_active=True,
            is_active=True,
            published_at__gte=cutoff_date,
        ).select_related('channel')

        if options['channel']:
            videos_qs = videos_qs.filter(channel__channel_id=options['channel'])
            self.stdout.write(f"📌 Filtering for channel: {options['channel']}")

        videos = list(videos_qs)
        total_videos = len(videos)
        self.stdout.write(f"📊 Found {total_videos} videos to update")

        if total_videos == 0:
            self.stdout.write(self.style.WARNING('⚠️  No videos found — nothing to update'))
            return

        # ── Process in batches ───────────────────────────────────────────────
        batch_size   = options['batch_size']
        updated      = 0
        errors       = 0
        now          = timezone.now()

        for i in range(0, total_videos, batch_size):
            batch      = videos[i:i + batch_size]
            video_ids  = [v.youtube_video_id for v in batch]
            batch_num  = i // batch_size + 1
            total_batches = (total_videos - 1) // batch_size + 1

            self.stdout.write(f"\n🔄 Batch {batch_num}/{total_batches}  ({len(batch)} videos)")

            try:
                response = youtube.videos().list(
                    part='statistics',
                    id=','.join(video_ids)
                ).execute()

                returned_ids = {item['id'] for item in response.get('items', [])}

                for item in response.get('items', []):
                    vid_id        = item['id']
                    current_views = int(item['statistics'].get('viewCount', 0))

                    video = next((v for v in batch if v.youtube_video_id == vid_id), None)
                    if not video:
                        continue

                    # ⭐ CORE CALL — stores timestamp-based 6h snapshot
                    video.save_6h_snapshot(current_views)
                    updated += 1

                    # Determine which section this video belongs to now
                    section_label = (
                        '🔥 Hot&New'  if video.in_hot_and_new()   else
                        '📈 Daily'    if video.in_daily_growth()   else
                        '📊 Weekly'   if video.in_weekly_growth()  else
                        '—  Archived'
                    )

                    hot_g    = video.get_hot_growth()    if video.in_hot_and_new()  else '-'
                    daily_g  = video.get_daily_growth()  if video.in_daily_growth() else '-'
                    weekly_g = video.get_weekly_growth() if video.in_weekly_growth() else '-'

                    self.stdout.write(
                        f"  ✅ {video.title[:35]:<35} | "
                        f"Views: {current_views:>10,} | "
                        f"Section: {section_label} | "
                        f"6h: {hot_g if hot_g != '-' else '-':>8} | "
                        f"24h: {daily_g if daily_g != '-' else '-':>8} | "
                        f"7d: {weekly_g if weekly_g != '-' else '-':>8}"
                    )

                # Warn about videos not returned (deleted / private)
                for video in batch:
                    if video.youtube_video_id not in returned_ids:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Not found on YouTube: {video.youtube_video_id}"
                            )
                        )

                time.sleep(0.1)   # stay within rate limits

            except HttpError as e:
                self.stdout.write(self.style.ERROR(f'❌ YouTube API error: {e}'))
                errors += len(batch)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Unexpected error: {e}'))
                errors += len(batch)

        # ── Summary ──────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 72)
        self.stdout.write(self.style.SUCCESS("✅  Update complete!"))
        self.stdout.write(f"   🕐 Run at  : {now.strftime('%Y-%m-%d %H:%M')} UTC")
        self.stdout.write(f"   ✅ Updated : {updated} videos")
        self.stdout.write(f"   ❌ Errors  : {errors} videos")

        # Section counts
        hot_count    = sum(1 for v in videos if v.in_hot_and_new())
        daily_count  = sum(1 for v in videos if v.in_daily_growth())
        weekly_count = sum(1 for v in videos if v.in_weekly_growth())
        self.stdout.write(f"\n   🔥 Hot & New   : {hot_count}")
        self.stdout.write(f"   📈 Daily Growth: {daily_count}")
        self.stdout.write(f"   📊 Weekly Growth: {weekly_count}")

        # Sample history
        self.stdout.write("\n📂 Sample snapshot history:")
        for video in videos[:3]:
            self.stdout.write(f"   • {video.title[:40]} | {video.get_history_summary()}")

        self.stdout.write("=" * 72)