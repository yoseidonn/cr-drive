from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404, FileResponse
from django.contrib import messages
from .models import File, Folder
from .forms import FileUploadForm, FolderCreateForm, RenameForm, MoveForm
from sharing.models import Permission
from django.contrib.auth.models import User
from django.conf import settings
import os
from .encryption import encrypt_file, decrypt_file
import mimetypes
import re

# Helper: check if user is superuser
def is_superuser(user):
    return user.is_superuser

# Helper: get user storage usage
def get_user_storage_usage(user):
    return sum(f.size for f in File.objects.filter(owner=user))

def get_breadcrumbs(folder):
    breadcrumbs = []
    while folder:
        breadcrumbs.insert(0, folder)
        folder = folder.parent
    return breadcrumbs

@login_required
def drive_view(request):
    folder_id = request.GET.get('folder')
    view_mode = request.GET.get('view', 'list')
    folder = None
    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id)
        if folder.owner != request.user and not Permission.objects.filter(folder=folder, user=request.user).exists():
            raise Http404()
        folders = folder.subfolders.all()
        files = folder.files.all()
        breadcrumbs = get_breadcrumbs(folder)
    else:
        folders = Folder.objects.filter(owner=request.user, parent=None)
        files = File.objects.filter(owner=request.user, folder__isnull=True)
        breadcrumbs = []

    # Handle forms in modals
    file_form = FileUploadForm()
    folder_form = FolderCreateForm()
    rename_form = RenameForm()
    move_form = MoveForm(user=request.user)
    show_upload_modal = False
    show_folder_modal = False
    show_rename_modal = False
    show_move_modal = False
    show_remove_modal = False
    rename_target = None
    move_target = None
    remove_target = None

    if request.method == 'POST':
        if 'upload_file' in request.POST:
            file_form = FileUploadForm(request.POST, request.FILES)
            if file_form.is_valid():
                upload = request.FILES['file']
                if upload.size > settings.MAX_FILE_SIZE:
                    messages.error(request, f'File size exceeds the limit of {settings.MAX_FILE_SIZE // (1024*1024)} MB.')
                    show_upload_modal = True
                else:
                    file_bytes = upload.read()
                    encrypted_bytes = encrypt_file(file_bytes)
                    file_obj = file_form.save(commit=False)
                    file_obj.owner = request.user
                    file_obj.name = upload.name
                    file_obj.size = len(encrypted_bytes)
                    if folder:
                        file_obj.folder = folder
                    usage = sum(f.size for f in File.objects.filter(owner=request.user))
                    if usage + file_obj.size > settings.TOTAL_SERVER_STORAGE * 0.02:
                        messages.error(request, 'Storage quota exceeded.')
                        show_upload_modal = True
                    else:
                        def sanitize_filename(name):
                            name = re.sub(r'[^\w\-. ]', '_', name)
                            return name[:100]
                        safe_name = sanitize_filename(upload.name)
                        user_folder = f'user_{request.user.id}'
                        folder_part = f'folder_{folder.id}' if folder else 'root'
                        file_path = f'files/{user_folder}/{folder_part}/{safe_name}'
                        abs_path = os.path.join(settings.MEDIA_ROOT, file_path)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        base, ext = os.path.splitext(safe_name)
                        counter = 1
                        unique_path = abs_path
                        unique_file_path = file_path
                        while os.path.exists(unique_path):
                            safe_name = f"{base}_{counter}{ext}"
                            unique_file_path = f'files/{user_folder}/{folder_part}/{safe_name}'
                            unique_path = os.path.join(settings.MEDIA_ROOT, unique_file_path)
                            counter += 1
                        with open(unique_path, 'wb') as f:
                            f.write(encrypted_bytes)
                        file_obj.file.name = unique_file_path
                        file_obj.save()
                        messages.success(request, 'File uploaded and encrypted successfully.')
                        return redirect(request.get_full_path())
            else:
                show_upload_modal = True
        elif 'create_folder' in request.POST:
            folder_form = FolderCreateForm(request.POST)
            if folder_form.is_valid():
                folder_obj = folder_form.save(commit=False)
                folder_obj.owner = request.user
                if folder:
                    folder_obj.parent = folder
                folder_obj.save()
                messages.success(request, 'Folder created successfully.')
                return redirect(request.get_full_path())
            else:
                show_folder_modal = True
        elif 'rename' in request.POST:
            rename_form = RenameForm(request.POST)
            target_type = request.POST.get('target_type')
            target_id = request.POST.get('target_id')
            if target_type == 'file':
                target = get_object_or_404(File, id=target_id)
            else:
                target = get_object_or_404(Folder, id=target_id)
            if (hasattr(target, 'owner') and target.owner == request.user) or request.user.is_superuser:
                if rename_form.is_valid():
                    target.name = rename_form.cleaned_data['name']
                    target.save()
                    messages.success(request, 'Renamed successfully.')
                    return redirect(request.get_full_path())
                else:
                    show_rename_modal = True
                    rename_target = target
            else:
                messages.error(request, 'Permission denied.')
        elif 'move' in request.POST:
            move_form = MoveForm(request.POST, user=request.user)
            target_type = request.POST.get('target_type')
            target_id = request.POST.get('target_id')
            if target_type == 'file':
                target = get_object_or_404(File, id=target_id)
            else:
                target = get_object_or_404(Folder, id=target_id)
            if (hasattr(target, 'owner') and target.owner == request.user) or request.user.is_superuser:
                if move_form.is_valid():
                    dest = move_form.cleaned_data['destination']
                    if target_type == 'file':
                        target.folder = dest
                    else:
                        target.parent = dest
                    target.save()
                    messages.success(request, 'Moved successfully.')
                    return redirect(request.get_full_path())
                else:
                    show_move_modal = True
                    move_target = target
            else:
                messages.error(request, 'Permission denied.')
        elif 'remove' in request.POST:
            target_type = request.POST.get('target_type')
            target_id = request.POST.get('target_id')
            if target_type == 'file':
                target = get_object_or_404(File, id=target_id)
            else:
                target = get_object_or_404(Folder, id=target_id)
            if (hasattr(target, 'owner') and target.owner == request.user) or request.user.is_superuser:
                if target_type == 'file':
                    target.file.delete()
                    target.delete()
                else:
                    # Delete all subfolders/files recursively
                    def delete_folder(folder):
                        for f in folder.files.all():
                            f.file.delete()
                            f.delete()
                        for sub in folder.subfolders.all():
                            delete_folder(sub)
                        folder.delete()
                    delete_folder(target)
                messages.success(request, 'Deleted successfully.')
                return redirect(request.get_full_path())
            else:
                messages.error(request, 'Permission denied.')
                show_remove_modal = True
                remove_target = target

    return render(request, 'storage/drive.html', {
        'folders': folders,
        'files': files,
        'current_folder': folder,
        'breadcrumbs': breadcrumbs,
        'view_mode': view_mode,
        'file_form': file_form,
        'folder_form': folder_form,
        'show_upload_modal': show_upload_modal,
        'show_folder_modal': show_folder_modal,
        'rename_form': rename_form,
        'move_form': move_form,
        'show_rename_modal': show_rename_modal,
        'show_move_modal': show_move_modal,
        'show_remove_modal': show_remove_modal,
        'rename_target': rename_target,
        'move_target': move_target,
        'remove_target': remove_target,
    })

@login_required
def folder_view(request, folder_id):
    folder = get_object_or_404(Folder, id=folder_id)
    if folder.owner != request.user and not Permission.objects.filter(folder=folder, user=request.user).exists():
        raise Http404()
    subfolders = folder.subfolders.all()
    files = folder.files.all()
    return render(request, 'storage/folder.html', {'folder': folder, 'subfolders': subfolders, 'files': files})

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.owner = request.user
            file_obj.size = file_obj.file.size
            usage = get_user_storage_usage(request.user)
            if usage + file_obj.size > settings.TOTAL_SERVER_STORAGE * 0.02:
                messages.error(request, 'Storage quota exceeded.')
            else:
                file_obj.save()
                messages.success(request, 'File uploaded successfully.')
                return redirect('drive')
    else:
        form = FileUploadForm()
    return render(request, 'storage/upload.html', {'form': form})

@login_required
def create_folder(request):
    if request.method == 'POST':
        form = FolderCreateForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.owner = request.user
            folder.save()
            messages.success(request, 'Folder created successfully.')
            return redirect('drive')
    else:
        form = FolderCreateForm()
    return render(request, 'storage/create_folder.html', {'form': form})

@login_required
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id)
    if file.owner == request.user or request.user.is_superuser:
        file.file.delete()
        file.delete()
        messages.success(request, 'File deleted.')
    else:
        messages.error(request, 'Permission denied.')
    return redirect('drive')

@login_required
def download_file(request, file_id):
    file = get_object_or_404(File, id=file_id)
    if file.owner != request.user and not Permission.objects.filter(file=file, user=request.user).exists() and not request.user.is_superuser:
        raise Http404()
    file_path = file.file.path
    if not os.path.exists(file_path):
        raise Http404()
    with open(file_path, 'rb') as f:
        encrypted_bytes = f.read()
        decrypted_bytes = decrypt_file(encrypted_bytes)
        if decrypted_bytes is None:
            raise Http404('File decryption failed.')
        response = HttpResponse(decrypted_bytes, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{file.name}"'
        return response

@login_required
def share_file(request, file_id):
    file = get_object_or_404(File, id=file_id)
    if file.owner != request.user:
        messages.error(request, 'Only the owner can share this file.')
        return redirect('drive')
    if request.method == 'POST':
        username = request.POST.get('username')
        access_level = request.POST.get('access_level')
        user = User.objects.filter(username=username).first()
        if user:
            Permission.objects.update_or_create(user=user, file=file, defaults={'access_level': access_level})
            messages.success(request, f'File shared with {username}.')
        else:
            messages.error(request, 'User not found.')
    return render(request, 'storage/share_file.html', {'file': file})

@login_required
def request_access(request, file_id):
    file = get_object_or_404(File, id=file_id)
    owner = file.owner
    # In a real app, send notification/email. Here, just show a message.
    messages.info(request, f'Access request sent to {owner.username}.')
    return redirect('drive')

@login_required
def accept_access(request, permission_id):
    perm = get_object_or_404(Permission, id=permission_id)
    if perm.file and perm.file.owner == request.user:
        perm.access_level = 'read'  # or 'write', as needed
        perm.save()
        messages.success(request, 'Access granted.')
    else:
        messages.error(request, 'Permission denied.')
    return redirect('drive')

@user_passes_test(is_superuser)
def superuser_dashboard(request):
    users = User.objects.all()
    return render(request, 'storage/superuser_dashboard.html', {'users': users})

@user_passes_test(is_superuser)
def superuser_user_files(request, user_id):
    user = get_object_or_404(User, id=user_id)
    files = File.objects.filter(owner=user)
    folders = Folder.objects.filter(owner=user)
    return render(request, 'storage/superuser_user_files.html', {'user': user, 'files': files, 'folders': folders})

@login_required
def view_file(request, file_id):
    file = get_object_or_404(File, id=file_id)
    if file.owner != request.user and not Permission.objects.filter(file=file, user=request.user).exists() and not request.user.is_superuser:
        raise Http404()
    file_path = file.file.path
    if not os.path.exists(file_path):
        raise Http404()
    ext = os.path.splitext(file.name)[1].lower()
    text_exts = ['.txt', '.csv', '.md', '.py', '.json', '.log']
    with open(file_path, 'rb') as f:
        encrypted_bytes = f.read()
        decrypted_bytes = decrypt_file(encrypted_bytes)
        if decrypted_bytes is None:
            raise Http404('File decryption failed.')
        if ext in text_exts:
            text = decrypted_bytes.decode(errors='replace')
            if request.method == 'POST':
                new_text = request.POST.get('file_content', '')
                # Save new content (re-encrypt and overwrite file)
                new_encrypted = encrypt_file(new_text.encode())
                with open(file_path, 'wb') as wf:
                    wf.write(new_encrypted)
                file.size = len(new_encrypted)
                file.save()
                messages.success(request, 'File saved.')
                return redirect('view_file', file_id=file.id)
            return render(request, 'storage/view_text_file.html', {'file': file, 'text': text})
        else:
            # For media, stream the file for browser preview
            mime, _ = mimetypes.guess_type(file.name)
            response = HttpResponse(decrypted_bytes, content_type=mime or 'application/octet-stream')
            response['Content-Disposition'] = f'inline; filename="{file.name}"'
            return response
