from django.db import models


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
    is_embeddable    = models.BooleanField(default=True,  help_text="False = YouTube blocked embedding. Hidden from all listings.")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']
        indexes  = [
            models.Index(fields=['channel', 'is_active']),
            models.Index(fields=['youtube_video_id']),
            models.Index(fields=['is_short']),
            models.Index(fields=['is_embeddable']),
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
                self.is_short = 0 < total_seconds <= 60
            except (ValueError, AttributeError):
                self.is_short = False
        super().save(*args, **kwargs)

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