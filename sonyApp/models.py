from django.db import models
from datetime import timedelta
from django.utils import timezone


class Channel(models.Model):
    """
    YouTube Channel model
    """
    channel_id         = models.CharField(max_length=100, unique=True)
    youtube_channel_id = models.CharField(max_length=100)
    name               = models.CharField(max_length=255)
    description        = models.TextField(blank=True)
    thumbnail_url      = models.URLField(blank=True)
    subscriber_count   = models.IntegerField(default=0)
    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_subscribe_url(self):
        return f"https://www.youtube.com/channel/{self.youtube_channel_id}?sub_confirmation=1"

    def get_channel_url(self):
        return f"https://www.youtube.com/channel/{self.youtube_channel_id}"


class Video(models.Model):
    """
    YouTube Video model
    """
    channel          = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='videos')
    youtube_video_id = models.CharField(max_length=100, unique=True)
    title            = models.CharField(max_length=255)
    description      = models.TextField(blank=True)
    thumbnail_url    = models.URLField(blank=True)
    duration         = models.CharField(max_length=20, blank=True)
    view_count       = models.IntegerField(default=0)
    like_count       = models.IntegerField(default=0)
    published_at     = models.DateTimeField()
    is_active        = models.BooleanField(default=True)
    is_short         = models.BooleanField(default=False, help_text="Is this a YouTube Short?")
    is_embeddable    = models.BooleanField(default=True, help_text="False = YouTube blocked embedding. Hidden from all listings.")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    # ─── GROWTH TRACKING (timestamp-based, 6h intervals) ───────────────────────
    view_count_history = models.JSONField(
        default=dict,
        help_text='6h snapshots: {"YYYY-MM-DD HH:00": view_count}'
    )
    base_snapshot_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the very first snapshot taken after publish. Used to determine section eligibility.'
    )
    last_snapshot_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the most recent snapshot stored.'
    )

    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['channel', 'is_active']),
            models.Index(fields=['youtube_video_id']),
            models.Index(fields=['is_short']),
            models.Index(fields=['is_embeddable']),
            models.Index(fields=['base_snapshot_timestamp']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Auto-detect YouTube Shorts by duration (<=60 seconds)."""
        if self.duration:
            try:
                parts = self.duration.split(':')
                if len(parts) == 2:
                    minutes, seconds = map(int, parts)
                    total_seconds = minutes * 60 + seconds
                elif len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    total_seconds = 0
                self.is_short = 0 < total_seconds <= 70
            except (ValueError, AttributeError):
                self.is_short = False
        super().save(*args, **kwargs)

    # ───────────────────────────────────────────────────────────────────────────
    # SNAPSHOT STORAGE
    # ───────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _snap_key(dt):
        import pytz
        IST = pytz.timezone('Asia/Kolkata')
        # Convert to IST if timezone-aware, else assume UTC
        if dt.tzinfo is not None:
            dt_ist = dt.astimezone(IST)
        else:
            import datetime
            dt_ist = dt.replace(tzinfo=datetime.timezone.utc).astimezone(IST)
        slot = (dt_ist.hour // 6) * 6
        return dt_ist.strftime(f'%Y-%m-%d {slot:02d}:00')

    def save_6h_snapshot(self, current_views):

        import logging
        logger = logging.getLogger(__name__)

        try:
            now = timezone.now()
            snap_key = self._snap_key(now)

            if not self.view_count_history:
                self.view_count_history = {}

            # First snapshot ever → set base
            if self.base_snapshot_timestamp is None:
                self.base_snapshot_timestamp = now
                logger.info(f"[{self.youtube_video_id}] Base snapshot set at {snap_key}")

            # Store snapshot
            self.view_count_history[snap_key] = current_views
            self.view_count = current_views
            self.last_snapshot_timestamp = now

            # ── Auto-cleanup: remove entries older than 720h (30 days) from base ──
            if self.base_snapshot_timestamp:
                cutoff = self.base_snapshot_timestamp + timedelta(hours=720)
                cutoff_key = self._snap_key(cutoff)
                keys_to_remove = [k for k in self.view_count_history if k > cutoff_key]
                # Actually remove keys BEFORE the base (shouldn't exist but safety check)
                base_key = self._snap_key(self.base_snapshot_timestamp)
                stale_keys = [
                    k for k in list(self.view_count_history.keys())
                    if k < base_key
                ]
                # Remove entries older than 30 days from NOW
                thirty_days_ago_key = self._snap_key(now - timedelta(hours=720))
                old_keys = [
                    k for k in list(self.view_count_history.keys())
                    if k < thirty_days_ago_key
                ]
                for k in old_keys:
                    del self.view_count_history[k]
                if old_keys:
                    logger.info(f"[{self.youtube_video_id}] Cleaned {len(old_keys)} old snapshots")

            self.save()

        except Exception as e:
            logger.error(f"Error saving 6h snapshot for {self.youtube_video_id}: {e}")

    # ───────────────────────────────────────────────────────────────────────────
    # SECTION ELIGIBILITY
    # ───────────────────────────────────────────────────────────────────────────

    def _age_hours(self):
        """Hours elapsed since published_at. Returns None if not published."""
        if not self.published_at:
            return None
        delta = timezone.now() - self.published_at
        return delta.total_seconds() / 3600

    def in_hot_and_new(self):
        """Section 1: 0h < age < 24h AND at least 2 snapshots stored."""
        age = self._age_hours()
        if age is None:
            return False
        return 0 < age < 24 and len(self.view_count_history) >= 2

    def in_daily_growth(self):
        """Section 2: 24h <= age < 168h."""
        age = self._age_hours()
        if age is None:
            return False
        return 24 <= age < 168

    def in_weekly_growth(self):
        """Section 3: 168h <= age < 720h."""
        age = self._age_hours()
        if age is None:
            return False
        return 168 <= age < 720

    # ───────────────────────────────────────────────────────────────────────────
    # CLOSEST SNAPSHOT LOOKUP
    # ───────────────────────────────────────────────────────────────────────────

    def _get_snapshot_near(self, target_dt):
        """
        Return the view count from the snapshot closest to target_dt.
        Searches within ±6h window. Returns None if not found.
        """
        if not self.view_count_history:
            return None

        from datetime import datetime as dt_cls, timezone as dt_timezone

        target_key = self._snap_key(target_dt)
        history = self.view_count_history

        # Direct hit
        if target_key in history:
            return history[target_key]

        # Find closest key within ±6h
        best_key = None
        best_diff = float('inf')

        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=dt_timezone.utc)

        for key in history:
            try:
                import pytz
                IST = pytz.timezone('Asia/Kolkata')
                key_dt = IST.localize(dt_cls.strptime(key, '%Y-%m-%d %H:%M'))
                diff = abs((key_dt - target_dt).total_seconds())
                if diff < best_diff and diff <= 21600:  # within 6h
                    best_diff = diff
                    best_key = key
            except ValueError:
                continue

        return history[best_key] if best_key else None

    def _current_views(self):
        """Return the most recent snapshot's view count."""
        if not self.view_count_history:
            return self.view_count or 0
        latest_key = max(self.view_count_history.keys())
        return self.view_count_history[latest_key]

    # ───────────────────────────────────────────────────────────────────────────
    # GROWTH CALCULATIONS
    # ───────────────────────────────────────────────────────────────────────────

    def get_hot_growth(self):
        """
        Section 1: growth since the PREVIOUS 6h snapshot.
        current_snapshot - snapshot_6h_ago
        Returns 0 if not in Section 1 or insufficient data.
        """
        if not self.in_hot_and_new():
            return 0

        now = timezone.now()
        current = self._current_views()
        prev = self._get_snapshot_near(now - timedelta(hours=6))

        if prev is None:
            # Fallback: use base snapshot
            prev = self._get_snapshot_near(self.base_snapshot_timestamp)

        if prev is None:
            return 0

        return max(0, current - prev)

    def get_daily_growth(self):
        """
        Section 2: rolling 24h growth.
        current_snapshot - snapshot_from_24h_ago
        On first entry (age == 24h): current - base_snapshot
        Returns 0 if not in Section 2 or insufficient data.
        """
        if not self.in_daily_growth():
            return 0

        now = timezone.now()
        current = self._current_views()
        past = self._get_snapshot_near(now - timedelta(hours=24))

        if past is None:
            return 0

        return max(0, current - past)

    def get_weekly_growth(self):
        """
        Section 3: rolling 7-day (168h) growth.
        current_snapshot - snapshot_from_168h_ago
        On first entry (age == 168h): current - base_snapshot
        Returns 0 if not in Section 3 or insufficient data.
        """
        if not self.in_weekly_growth():
            return 0

        now = timezone.now()
        current = self._current_views()
        past = self._get_snapshot_near(now - timedelta(hours=168))

        if past is None:
            return 0

        return max(0, current - past)

    # ───────────────────────────────────────────────────────────────────────────
    # DISPLAY HELPERS
    # ───────────────────────────────────────────────────────────────────────────

    def get_growth_label(self, section=None):
        """Return formatted growth label for use in templates."""
        if section == 'hot':
            growth = self.get_hot_growth()
            return f"+{growth:,} in last 6h"
        elif section == 'daily':
            growth = self.get_daily_growth()
            return f"+{growth:,} in 24h"
        elif section == 'weekly':
            growth = self.get_weekly_growth()
            return f"+{growth:,} this week"
        return ""

    def get_history_summary(self):
        """Return summary of stored history (for management command output)."""
        if not self.view_count_history:
            return "No history available"
        dates = sorted(self.view_count_history.keys())
        return f"{len(dates)} snapshots | {dates[0]} → {dates[-1]}"

    # ───────────────────────────────────────────────────────────────────────────
    # LEGACY COMPAT (keep old callers working during transition)
    # ───────────────────────────────────────────────────────────────────────────

    def get_today_growth(self):
        return self.get_daily_growth()

    # ───────────────────────────────────────────────────────────────────────────
    # URL HELPERS
    # ───────────────────────────────────────────────────────────────────────────

    def get_watch_url(self):
        if self.is_short:
            return f"https://www.youtube.com/shorts/{self.youtube_video_id}"
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"

    def get_embed_url(self):
        return f"https://www.youtube.com/embed/{self.youtube_video_id}"

    def get_duration_seconds(self):
        if not self.duration:
            return 0
        try:
            parts = self.duration.split(':')
            if len(parts) == 2:
                m, s = map(int, parts)
                return m * 60 + s
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
        except (ValueError, AttributeError):
            return 0
        return 0

    def get_formatted_duration(self):
        if not self.duration:
            return ""
        parts = self.duration.split(':')
        if len(parts) == 2:
            return f"{int(parts[0])}:{int(parts[1]):02d}"
        if len(parts) == 3:
            return f"{int(parts[0])}:{int(parts[1]):02d}:{int(parts[2]):02d}"
        return self.duration