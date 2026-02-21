# sonyApp/admin.py
from django.contrib import admin
from .models import Channel, Video  # Removed Subscription import

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_id', 'youtube_channel_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'channel_id', 'youtube_channel_id']
    readonly_fields = ['created_at']

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'channel', 'youtube_video_id', 'published_at', 'is_active']
    list_filter = ['channel', 'is_active', 'published_at']
    search_fields = ['title', 'youtube_video_id']
    readonly_fields = ['published_at']

