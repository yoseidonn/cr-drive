from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.

class Folder(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subfolders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
        ('ask', 'Ask'),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    share_token = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class File(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='files', null=True, blank=True)
    file = models.FileField(upload_to='files/')
    size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
        ('ask', 'Ask'),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    share_token = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class AccessRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'file', 'folder')
    def __str__(self):
        target = self.file if self.file else self.folder
        return f"{self.user.username} requests {target} ({self.status})"
