from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib import messages
from .models import File, Folder, AccessRequest
from .forms import FileUploadForm, FolderCreateForm, RenameForm, MoveForm
from sharing.models import Permission
from django.contrib.auth.models import User
from django.conf import settings
import os
from .encryption import encrypt_file, decrypt_file
import mimetypes
import re
from django.core.files.base import File as DjangoFile
import logging
from django.db import models
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# Helper: get user storage usage
def get_user_storage_usage(user):
    return sum(f.size for f in File.objects.filter(owner=user))

def get_breadcrumbs(folder):
    breadcrumbs = []
    while folder:
        breadcrumbs.insert(0, folder)
        folder = folder.parent
    return breadcrumbs

class IsSuperuserMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class DriveView(LoginRequiredMixin, View):
    template_name = 'storage/drive.html'

    def get(self, request):
        folder_id = request.GET.get('folder')
        view_mode = request.GET.get('view', 'list')
        folder = None
        user = request.user
        # Robust folder_id validation
        try:
            folder_id_int = int(folder_id)
            if folder_id_int > 0:
                folder = get_object_or_404(Folder, id=folder_id_int)
            else:
                folder = None
        except (TypeError, ValueError):
            folder = None
        if folder:
            # Check folder visibility
            is_owner = folder.owner == user or user.is_superuser
            is_shared = Permission.objects.filter(folder=folder, user=user).exists()
            if not (is_owner or is_shared or folder.visibility in ['public', 'ask']):
                raise Http404()
            # Subfolders
            shared_folder_ids = Permission.objects.filter(user=user, folder__in=folder.subfolders.all()).values_list('folder_id', flat=True)
            folders = folder.subfolders.filter(
                models.Q(owner=user) |
                models.Q(visibility='public') |
                models.Q(visibility='ask') |
                models.Q(id__in=shared_folder_ids)
            ).distinct()
            # Files
            shared_file_ids = Permission.objects.filter(user=user, file__in=folder.files.all()).values_list('file_id', flat=True)
            files = folder.files.filter(
                models.Q(owner=user) |
                models.Q(visibility='public') |
                models.Q(visibility='ask') |
                models.Q(id__in=shared_file_ids)
            ).distinct()
            breadcrumbs = get_breadcrumbs(folder)
        else:
            root_folders = Folder.objects.filter(parent=None)
            shared_folder_ids = Permission.objects.filter(user=user, folder__in=root_folders).values_list('folder_id', flat=True)
            folders = root_folders.filter(
                models.Q(owner=user) |
                models.Q(visibility='public') |
                models.Q(visibility='ask') |
                models.Q(id__in=shared_folder_ids)
            ).distinct()
            root_files = File.objects.filter(folder__isnull=True)
            shared_file_ids = Permission.objects.filter(user=user, file__in=root_files).values_list('file_id', flat=True)
            files = root_files.filter(
                models.Q(owner=user) |
                models.Q(visibility='public') |
                models.Q(visibility='ask') |
                models.Q(id__in=shared_file_ids)
            ).distinct()
            breadcrumbs = []
        context = {
            'folders': folders,
            'files': files,
            'current_folder': folder,
            'breadcrumbs': breadcrumbs,
            'view_mode': view_mode,
            'file_form': FileUploadForm(),
            'folder_form': FolderCreateForm(),
            'rename_form': RenameForm(),
            'move_form': MoveForm(user=user),
            'show_upload_modal': False,
            'show_folder_modal': False,
            'show_rename_modal': False,
            'show_move_modal': False,
            'show_remove_modal': False,
            'rename_target': None,
            'move_target': None,
            'remove_target': None,
        }
        # Add sets of folder/file IDs the user can share
        context['can_share_folder_ids'] = set(Permission.objects.filter(user=user, folder__in=folders).values_list('folder_id', flat=True))
        context['can_share_file_ids'] = set(Permission.objects.filter(user=user, file__in=files).values_list('file_id', flat=True))
        # Add set of file IDs with pending access requests
        context['pending_access_file_ids'] = set(AccessRequest.objects.filter(user=user, file__in=files, status='pending').values_list('file_id', flat=True))
        # Optionally, for folders:
        context['pending_access_folder_ids'] = set(AccessRequest.objects.filter(user=user, folder__in=folders, status='pending').values_list('folder_id', flat=True))
        # Add count of pending requests for owner's files/folders
        pending_count = 0
        if user.is_authenticated:
            pending_count = AccessRequest.objects.filter(
                status='pending',
                file__owner=user
            ).count() + AccessRequest.objects.filter(
                status='pending',
                folder__owner=user
            ).count()
        context['pending_access_request_count'] = pending_count
        return render(request, self.template_name, context)

    def post(self, request):
        folder_id = request.GET.get('folder')
        folder = None
        # Robust folder_id validation
        try:
            folder_id_int = int(folder_id)
            if folder_id_int > 0:
                folder = get_object_or_404(Folder, id=folder_id_int)
            else:
                folder = None
        except (TypeError, ValueError):
            folder = None
        view_mode = request.GET.get('view', 'list')
        # Rebuild context for error display
        folders = folder.subfolders.all() if folder else Folder.objects.filter(owner=request.user, parent=None)
        files = folder.files.all() if folder else File.objects.filter(owner=request.user, folder__isnull=True)
        breadcrumbs = get_breadcrumbs(folder) if folder else []
        context = {
            'folders': folders,
            'files': files,
            'current_folder': folder,
            'breadcrumbs': breadcrumbs,
            'view_mode': view_mode,
            'file_form': FileUploadForm(),
            'folder_form': FolderCreateForm(),
            'rename_form': RenameForm(),
            'move_form': MoveForm(user=request.user),
            'show_upload_modal': False,
            'show_folder_modal': False,
            'show_rename_modal': False,
            'show_move_modal': False,
            'show_remove_modal': False,
            'rename_target': None,
            'move_target': None,
            'remove_target': None,
        }
        if 'upload_file' in request.POST:
            file_form = FileUploadForm(request.POST, request.FILES)
            if file_form.is_valid():
                upload = request.FILES['file']
                if upload.size > settings.MAX_FILE_SIZE:
                    return JsonResponse({'status': 'error', 'message': f'File size exceeds the limit of {settings.MAX_FILE_SIZE // (1024*1024)} MB.'})
                file_bytes = upload.read()
                encrypted_bytes = encrypt_file(file_bytes)
                file_obj = file_form.save(commit=False)
                file_obj.owner = request.user
                file_obj.name = upload.name
                file_obj.size = len(encrypted_bytes)
                if folder:
                    file_obj.folder = folder
                usage = get_user_storage_usage(request.user)
                if usage + file_obj.size > settings.USER_STORAGE_QUOTA:
                    return JsonResponse({'status': 'error', 'message': 'Storage quota exceeded.'})
                def sanitize_filename(name):
                    name = re.sub(r'[\w\-. ]', '_', name)
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
                with open(unique_path, 'rb') as f:
                    file_obj.file.save(safe_name, DjangoFile(f), save=False)
                file_obj.save()
                return JsonResponse({'status': 'success', 'message': 'File uploaded and encrypted successfully.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid form.'})
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
                context['show_folder_modal'] = True
            context['folder_form'] = folder_form
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
                    context['show_rename_modal'] = True
                    context['rename_target'] = target
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
                    context['show_move_modal'] = True
                    context['move_target'] = target
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
                context['show_remove_modal'] = True
                context['remove_target'] = target
        return render(request, self.template_name, context)

class DownloadFileView(LoginRequiredMixin, View):
    def get(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        user = request.user
        is_owner = file.owner == user or user.is_superuser
        is_shared = Permission.objects.filter(file=file, user=user).exists()
        if not (is_owner or is_shared or file.visibility == 'public'):
            if file.visibility == 'ask':
                messages.error(request, 'You must request access to this file.')
                return redirect('drive')
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

class ViewFileView(LoginRequiredMixin, View):
    template_name = 'storage/view_text_file.html'
    def get(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        user = request.user
        is_owner = file.owner == user or user.is_superuser
        is_shared = Permission.objects.filter(file=file, user=user).exists()
        if not (is_owner or is_shared or file.visibility == 'public'):
            if file.visibility == 'ask':
                messages.error(request, 'You must request access to this file.')
                return redirect('drive')
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
                return render(request, self.template_name, {'file': file, 'text': text})
            else:
                mime, _ = mimetypes.guess_type(file.name)
                response = HttpResponse(decrypted_bytes, content_type=mime or 'application/octet-stream')
                response['Content-Disposition'] = f'inline; filename="{file.name}"'
                return response
    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        user = request.user
        is_owner = file.owner == user or user.is_superuser
        is_shared = Permission.objects.filter(file=file, user=user).exists()
        if not (is_owner or is_shared or file.visibility == 'public'):
            if file.visibility == 'ask':
                messages.error(request, 'You must request access to this file.')
                return redirect('drive')
            raise Http404()
        file_path = file.file.path
        if not os.path.exists(file_path):
            raise Http404()
        ext = os.path.splitext(file.name)[1].lower()
        text_exts = ['.txt', '.csv', '.md', '.py', '.json', '.log']
        if ext in text_exts:
            new_text = request.POST.get('file_content', '')
            new_encrypted = encrypt_file(new_text.encode())
            with open(file_path, 'wb') as wf:
                wf.write(new_encrypted)
            file.size = len(new_encrypted)
            file.save()
            messages.success(request, 'File saved.')
            return redirect('view_file', file_id=file.id)
        else:
            return self.get(request, file_id)

class ShareFileView(LoginRequiredMixin, View):
    template_name = 'storage/share_file.html'
    def get(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        if file.owner != request.user:
            messages.error(request, 'Only the owner can share this file.')
            return redirect('drive')
        return render(request, self.template_name, {'file': file})
    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        if file.owner != request.user:
            messages.error(request, 'Only the owner can share this file.')
            return redirect('drive')
        username = request.POST.get('username')
        access_level = request.POST.get('access_level')
        user = User.objects.filter(username=username).first()
        if user:
            Permission.objects.update_or_create(user=user, file=file, defaults={'access_level': access_level})
            messages.success(request, f'File shared with {username}.')
        else:
            messages.error(request, 'User not found.')
        return render(request, self.template_name, {'file': file})

class RequestAccessView(LoginRequiredMixin, View):
    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        owner = file.owner
        messages.info(request, f'Access request sent to {owner.username}.')
        return redirect('drive')

class AcceptAccessView(LoginRequiredMixin, View):
    def post(self, request, permission_id):
        perm = get_object_or_404(Permission, id=permission_id)
        if perm.file and perm.file.owner == request.user:
            perm.access_level = 'read'
            perm.save()
            messages.success(request, 'Access granted.')
        else:
            messages.error(request, 'Permission denied.')
        return redirect('drive')

class SuperuserDashboardView(IsSuperuserMixin, TemplateView):
    template_name = 'storage/superuser_dashboard.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context

class SuperuserUserFilesView(IsSuperuserMixin, TemplateView):
    template_name = 'storage/superuser_user_files.html'
    def get_context_data(self, **kwargs):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        context = super().get_context_data(**kwargs)
        context['user'] = user
        context['files'] = File.objects.filter(owner=user)
        context['folders'] = Folder.objects.filter(owner=user)
        return context

class RequestAccessToFileView(LoginRequiredMixin, View):
    def post(self, request, file_id):
        file = get_object_or_404(File, id=file_id)
        user = request.user
        if file.owner == user or Permission.objects.filter(file=file, user=user).exists():
            messages.info(request, 'You already have access.')
        else:
            ar, created = AccessRequest.objects.get_or_create(user=user, file=file)
            if created:
                messages.success(request, 'Access request sent.')
            else:
                messages.info(request, 'You have already requested access.')
        return redirect('drive')

class RequestAccessToFolderView(LoginRequiredMixin, View):
    def post(self, request, folder_id):
        folder = get_object_or_404(Folder, id=folder_id)
        user = request.user
        if folder.owner == user or Permission.objects.filter(folder=folder, user=user).exists():
            messages.info(request, 'You already have access.')
        else:
            ar, created = AccessRequest.objects.get_or_create(user=user, folder=folder)
            if created:
                messages.success(request, 'Access request sent.')
            else:
                messages.info(request, 'You have already requested access.')
        return redirect('drive')

class OwnerAccessRequestsView(LoginRequiredMixin, View):
    template_name = 'storage/access_requests.html'
    def get(self, request):
        user = request.user
        # All requests for files/folders owned by this user
        file_requests = AccessRequest.objects.filter(file__owner=user, status='pending')
        folder_requests = AccessRequest.objects.filter(folder__owner=user, status='pending')
        return render(request, self.template_name, {'file_requests': file_requests, 'folder_requests': folder_requests})

class ApproveAccessRequestView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        ar = get_object_or_404(AccessRequest, id=request_id)
        if (ar.file and ar.file.owner == request.user) or (ar.folder and ar.folder.owner == request.user):
            ar.status = 'approved'
            ar.save()
            # Grant permission
            if ar.file:
                Permission.objects.get_or_create(user=ar.user, file=ar.file, defaults={'access_level': 'read'})
            if ar.folder:
                Permission.objects.get_or_create(user=ar.user, folder=ar.folder, defaults={'access_level': 'read'})
            messages.success(request, 'Access granted.')
        else:
            messages.error(request, 'Permission denied.')
        return redirect('owner_access_requests')

class RejectAccessRequestView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        ar = get_object_or_404(AccessRequest, id=request_id)
        if (ar.file and ar.file.owner == request.user) or (ar.folder and ar.folder.owner == request.user):
            ar.status = 'rejected'
            ar.save()
            messages.info(request, 'Access request rejected.')
        else:
            messages.error(request, 'Permission denied.')
        return redirect('owner_access_requests')

class ShareLinkFileView(View):
    def get(self, request, token):
        file = get_object_or_404(File, share_token=token)
        if file.visibility == 'private':
            banner = "This file is private. To share, set its visibility to 'ask' or 'public'."
            return render(request, 'storage/drive.html', {
                'folders': [],
                'files': [],
                'current_folder': None,
                'breadcrumbs': [],
                'view_mode': 'list',
                'file_form': FileUploadForm(),
                'folder_form': FolderCreateForm(),
                'rename_form': RenameForm(),
                'move_form': None,
                'show_upload_modal': False,
                'show_folder_modal': False,
                'show_rename_modal': False,
                'show_move_modal': False,
                'show_remove_modal': False,
                'rename_target': None,
                'move_target': None,
                'remove_target': None,
                'shared_file': None,
                'share_banner': banner,
            })
        user = request.user if request.user.is_authenticated else None
        is_owner = user and (file.owner == user or user.is_superuser)
        is_shared = user and Permission.objects.filter(file=file, user=user).exists()
        can_view = file.visibility == 'public' or is_owner or is_shared
        # If not accessible
        if not can_view:
            if file.visibility == 'ask':
                # If not logged in, prompt login
                if not user:
                    return render(request, 'storage/drive.html', {
                        'folders': [],
                        'files': [],
                        'current_folder': None,
                        'breadcrumbs': [],
                        'view_mode': 'list',
                        'file_form': FileUploadForm(),
                        'folder_form': FolderCreateForm(),
                        'rename_form': RenameForm(),
                        'move_form': None,
                        'show_upload_modal': False,
                        'show_folder_modal': False,
                        'show_rename_modal': False,
                        'show_move_modal': False,
                        'show_remove_modal': False,
                        'rename_target': None,
                        'move_target': None,
                        'remove_target': None,
                        'shared_file': None,
                        'share_banner': "<a href='/accounts/login/'>Log in</a> to request access to this file.",
                    })
                # Show request access form
                return render(request, 'storage/share_file.html', {'file': file, 'show_request_access': True})
            # Not public, not shared, not owner
            banner = "This file is not public. "
            if not user:
                banner += "<a href='/accounts/login/'>Log in</a> to see if you have access."
            else:
                banner += "You do not have access to this file."
            return render(request, 'storage/drive.html', {
                'folders': [],
                'files': [],
                'current_folder': None,
                'breadcrumbs': [],
                'view_mode': 'list',
                'file_form': FileUploadForm(),
                'folder_form': FolderCreateForm(),
                'rename_form': RenameForm(),
                'move_form': None,
                'show_upload_modal': False,
                'show_folder_modal': False,
                'show_rename_modal': False,
                'show_move_modal': False,
                'show_remove_modal': False,
                'rename_target': None,
                'move_target': None,
                'remove_target': None,
                'shared_file': None,
                'share_banner': banner,
            })
        # If accessible, show in drive view with banner if not owner
        folder = file.folder
        breadcrumbs = get_breadcrumbs(folder) if folder else []
        share_banner = None
        if not is_owner:
            if user:
                share_banner = f"Shared by {file.owner.username}"
            else:
                share_banner = f"This file is shared by {file.owner.username}. <a href='/accounts/login/'>Log in</a> for more features."
        context = {
            'folders': [],
            'files': [file],
            'current_folder': folder,
            'breadcrumbs': breadcrumbs,
            'view_mode': 'list',
            'file_form': FileUploadForm(),
            'folder_form': FolderCreateForm(),
            'rename_form': RenameForm(),
            'move_form': MoveForm(user=user) if user else None,
            'show_upload_modal': False,
            'show_folder_modal': False,
            'show_rename_modal': False,
            'show_move_modal': False,
            'show_remove_modal': False,
            'rename_target': None,
            'move_target': None,
            'remove_target': None,
            'shared_file': file,
            'share_banner': share_banner,
        }
        return render(request, 'storage/drive.html', context)

class ShareLinkFolderView(View):
    def get(self, request, token):
        folder = get_object_or_404(Folder, share_token=token)
        if folder.visibility == 'private':
            banner = "This folder is private. To share, set its visibility to 'ask' or 'public'."
            return render(request, 'storage/drive.html', {
                'folders': [],
                'files': [],
                'current_folder': None,
                'breadcrumbs': [],
                'view_mode': 'list',
                'file_form': FileUploadForm(),
                'folder_form': FolderCreateForm(),
                'rename_form': RenameForm(),
                'move_form': None,
                'show_upload_modal': False,
                'show_folder_modal': False,
                'show_rename_modal': False,
                'show_move_modal': False,
                'show_remove_modal': False,
                'rename_target': None,
                'move_target': None,
                'remove_target': None,
                'share_banner': banner,
            })
        user = request.user if request.user.is_authenticated else None
        is_owner = user and (folder.owner == user or user.is_superuser)
        is_shared = user and Permission.objects.filter(folder=folder, user=user).exists()
        if folder.visibility == 'public' or is_owner or is_shared:
            files = folder.files.all() if (is_owner or is_shared) else folder.files.filter(visibility='public')
            subfolders = folder.subfolders.all() if (is_owner or is_shared) else folder.subfolders.filter(visibility='public')
            return render(request, 'storage/drive.html', {
                'folders': subfolders,
                'files': files,
                'current_folder': folder,
                'breadcrumbs': get_breadcrumbs(folder),
                'view_mode': 'list',
                'file_form': FileUploadForm(),
                'folder_form': FolderCreateForm(),
                'rename_form': RenameForm(),
                'move_form': MoveForm(user=user) if user else None,
                'show_upload_modal': False,
                'show_folder_modal': False,
                'show_rename_modal': False,
                'show_move_modal': False,
                'show_remove_modal': False,
                'rename_target': None,
                'move_target': None,
                'remove_target': None,
            })
        elif folder.visibility == 'ask':
            return render(request, 'storage/share_file.html', {'folder': folder, 'show_request_access': True})
        else:
            # Private: block all access, even to inner public/ask files
            banner = "This folder is not public. "
            if not user:
                banner += "<a href='/accounts/login/'>Log in</a> to see if you have access."
            else:
                banner += "You do not have access to this folder."
            return render(request, 'storage/drive.html', {
                'folders': [],
                'files': [],
                'current_folder': None,
                'breadcrumbs': [],
                'view_mode': 'list',
                'file_form': FileUploadForm(),
                'folder_form': FolderCreateForm(),
                'rename_form': RenameForm(),
                'move_form': None,
                'show_upload_modal': False,
                'show_folder_modal': False,
                'show_rename_modal': False,
                'show_move_modal': False,
                'show_remove_modal': False,
                'rename_target': None,
                'move_target': None,
                'remove_target': None,
                'share_banner': banner,
            })

# --- AJAX endpoints for sharing modal ---
class ShareInfoView(LoginRequiredMixin, View):
    def get(self, request, type, id):
        user = request.user
        # If owner requests a share link for a private item, auto-switch to 'ask' mode for secure sharing
        if type == 'file':
            obj = get_object_or_404(File, id=id)
            if obj.visibility == 'private' and (obj.owner == user or user.is_superuser):
                obj.visibility = 'ask'
                obj.save()
            share_link = request.build_absolute_uri(reverse('share_link_file', args=[obj.share_token]))
            shared_users = list(Permission.objects.filter(file=obj).values('user__username', 'access_level'))
        else:
            obj = get_object_or_404(Folder, id=id)
            if obj.visibility == 'private' and (obj.owner == user or user.is_superuser):
                obj.visibility = 'ask'
                obj.save()
            share_link = request.build_absolute_uri(reverse('share_link_folder', args=[obj.share_token]))
            shared_users = list(Permission.objects.filter(folder=obj).values('user__username', 'access_level'))
        is_owner = obj.owner == user or user.is_superuser
        return JsonResponse({
            'name': obj.name,
            'share_link': share_link,
            'visibility': obj.visibility,
            'is_owner': is_owner,
            'shared_users': shared_users,
        })

@method_decorator(require_POST, name='dispatch')
class ShareUpdateView(LoginRequiredMixin, View):
    def post(self, request, type, id):
        user = request.user
        visibility = request.POST.get('visibility')
        if type == 'file':
            obj = get_object_or_404(File, id=id)
        else:
            obj = get_object_or_404(Folder, id=id)
        if obj.owner != user and not user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        if visibility in ['public', 'private', 'ask']:
            obj.visibility = visibility
            obj.save()
            return JsonResponse({'status': 'success', 'visibility': obj.visibility})
        return JsonResponse({'status': 'error', 'message': 'Invalid visibility.'}, status=400)

@method_decorator(require_POST, name='dispatch')
class ShareAddUserView(LoginRequiredMixin, View):
    def post(self, request, type, id):
        user = request.user
        username = request.POST.get('username')
        access_level = request.POST.get('access_level', 'read')
        target_user = User.objects.filter(username=username).first()
        if not target_user:
            return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)
        if type == 'file':
            obj = get_object_or_404(File, id=id)
            perm, created = Permission.objects.update_or_create(user=target_user, file=obj, defaults={'access_level': access_level})
        else:
            obj = get_object_or_404(Folder, id=id)
            perm, created = Permission.objects.update_or_create(user=target_user, folder=obj, defaults={'access_level': access_level})
        if obj.owner != user and not user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        return JsonResponse({'status': 'success', 'user': username, 'access_level': access_level})

@method_decorator(require_POST, name='dispatch')
class ShareRemoveUserView(LoginRequiredMixin, View):
    def post(self, request, type, id):
        user = request.user
        username = request.POST.get('username')
        target_user = User.objects.filter(username=username).first()
        if not target_user:
            return JsonResponse({'status': 'error', 'message': 'User not found.'}, status=404)
        if type == 'file':
            obj = get_object_or_404(File, id=id)
            perm = Permission.objects.filter(user=target_user, file=obj)
        else:
            obj = get_object_or_404(Folder, id=id)
            perm = Permission.objects.filter(user=target_user, folder=obj)
        if obj.owner != user and not user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        perm.delete()
        return JsonResponse({'status': 'success', 'user': username})
