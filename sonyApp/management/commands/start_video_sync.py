
from django.core.management.base import BaseCommand
from sonyApp.tasks import sync_recent_videos


class Command(BaseCommand):
    help = 'Start automatic video synchronization'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting automatic video sync...'))
        
        # Start the background task
        sync_recent_videos(repeat=3600)  # Repeat every hour
        
        self.stdout.write(self.style.SUCCESS(
            '✅ Video sync started!\n'
            '   - Checking for new videos every hour\n'
            '   - Running in background automatically\n'
            '   - No manual commands needed!\n'
        ))
