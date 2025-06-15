from django.core.management.base import BaseCommand
from storage.models import File, Folder
import uuid

class Command(BaseCommand):
    help = 'Assign share_token to all files and folders missing it.'

    def handle(self, *args, **options):
        updated_folders = 0
        updated_files = 0
        for folder in Folder.objects.filter(share_token__isnull=True):
            folder.share_token = uuid.uuid4().hex
            folder.save()
            updated_folders += 1
        for file in File.objects.filter(share_token__isnull=True):
            file.share_token = uuid.uuid4().hex
            file.save()
            updated_files += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated_folders} folders and {updated_files} files with missing share_token.')) 