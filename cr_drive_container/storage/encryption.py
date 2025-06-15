from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

fernet = Fernet(settings.FILE_ENCRYPTION_KEY.encode())

def encrypt_file(file_bytes):
    return fernet.encrypt(file_bytes)

def decrypt_file(encrypted_bytes):
    try:
        return fernet.decrypt(encrypted_bytes)
    except InvalidToken:
        return None 