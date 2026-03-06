from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Authentication
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # Channel pages
    path('channel/<str:channel_id>/', views.channel_detail, name='channel_detail'),

    # Video player
    path('channel/<str:channel_id>/video/<str:video_id>/', views.video_player, name='video_player'),

    # Search
    path('api/search/videos/', views.search_videos, name='search_videos'),

    # Channel APIs
    path('api/channels/dropdown/', views.channels_dropdown_api, name='channels_dropdown_api'),
    path('api/channels/<str:channel_id>/preview/', views.channel_preview_api, name='channel_preview_api'),

    # Video APIs
    path('api/video/flag-unembeddable/', views.flag_unembeddable, name='flag_unembeddable'),

    # Trending / Growth
    path('api/trending/', views.api_trending, name='api_trending'),

    # Enquiry
    path('api/enquiry/', views.enquiry, name='enquiry'),

    #Growth page:
    path('growth/', views.growth_page, name='growth_page'),
    
    # Artists pages
    path('artists/',         views.artists_page,   name='artists_page'),
    path('artists/videos/', views.artist_videos,  name='artist_videos'),

    # ── Cron job endpoints ──────────────────────────────────────
    path('api/health/', views.health_check, name='health_check'),                        # CRON 1 — every 5-10 min
    path('api/auto-fetch/', views.auto_fetch_videos, name='auto_fetch_videos'),          # CRON 2 — every 10 min
    path('api/update-stats/', views.auto_update_stats, name='auto_update_stats'),        # CRON 3 — every 6 hours
    path('api/update-stats-full/', views.auto_update_stats_full, name='auto_update_stats_full'),  # CRON 4 — daily
]