from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication (using social_django only)
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Channel pages
    path('channel/<str:channel_id>/', views.channel_detail, name='channel_detail'),
    
    # Video player
    path('channel/<str:channel_id>/video/<str:video_id>/', views.video_player, name='video_player'),
    path('api/search/videos/', views.search_videos, name='search_videos'),

     # Channel dropdown API
    path('api/channels/dropdown/', views.channels_dropdown_api, name='channels_dropdown_api'),
    
    # Channel preview API
    path('api/channels/<str:channel_id>/preview/', views.channel_preview_api, name='channel_preview_api'),

    path('api/video/flag-unembeddable/', views.flag_unembeddable, name='flag_unembeddable'),

    # Auto-fetch endpoints
    path('api/auto-fetch/', views.auto_fetch_videos, name='auto_fetch_videos'),
    path('api/health/', views.health_check, name='health_check'),
    path('api/fetch-all/', views.fetch_all_channel_videos, name='fetch_all_channel'),
    path('api/fetch-all-channels/', views.fetch_all_videos, name='fetch_all_channels'),

]