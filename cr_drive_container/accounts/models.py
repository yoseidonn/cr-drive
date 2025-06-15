from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Add more fields as needed, e.g. avatar, bio, etc.
    
    def __str__(self):
        return self.user.username
