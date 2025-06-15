from django.db import models
from django.contrib.auth.models import User
from storage.models import File, Folder

class Permission(models.Model):
    READ = 'read'
    WRITE = 'write'
    ACCESS_LEVELS = [
        (READ, 'Read'),
        (WRITE, 'Write'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE)
    access_level = models.CharField(max_length=5, choices=ACCESS_LEVELS)

    class Meta:
        unique_together = ('user', 'file', 'folder')

    def __str__(self):
        target = self.file if self.file else self.folder
        return f"{self.user.username} - {target} ({self.access_level})"
