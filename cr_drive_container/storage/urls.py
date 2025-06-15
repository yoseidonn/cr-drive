from django.urls import path
from . import views

urlpatterns = [
    path('drive/', views.drive_view, name='drive'),
    path('folder/<int:folder_id>/', views.folder_view, name='folder'),
    path('upload/', views.upload_file, name='upload_file'),
    path('create_folder/', views.create_folder, name='create_folder'),
    path('delete_file/<int:file_id>/', views.delete_file, name='delete_file'),
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('share/<int:file_id>/', views.share_file, name='share_file'),
    path('request_access/<int:file_id>/', views.request_access, name='request_access'),
    path('accept_access/<int:permission_id>/', views.accept_access, name='accept_access'),
    # Superuser dashboard
    path('superuser/', views.superuser_dashboard, name='superuser_dashboard'),
    path('superuser/user/<int:user_id>/', views.superuser_user_files, name='superuser_user_files'),
    path('view/<int:file_id>/', views.view_file, name='view_file'),
] 