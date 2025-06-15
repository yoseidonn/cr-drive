from django.urls import path
from .views import (
    DriveView, DownloadFileView, ViewFileView, ShareFileView,
    RequestAccessView, AcceptAccessView, SuperuserDashboardView, SuperuserUserFilesView,
    RequestAccessToFileView, RequestAccessToFolderView, OwnerAccessRequestsView, ApproveAccessRequestView, RejectAccessRequestView,
    ShareLinkFileView, ShareLinkFolderView,
    ShareInfoView, ShareUpdateView, ShareAddUserView, ShareRemoveUserView
)

urlpatterns = [
    path('drive/', DriveView.as_view(), name='drive'),
    path('download/<int:file_id>/', DownloadFileView.as_view(), name='download_file'),
    path('share/<int:file_id>/', ShareFileView.as_view(), name='share_file'),
    path('request_access/<int:file_id>/', RequestAccessView.as_view(), name='request_access'),
    path('accept_access/<int:permission_id>/', AcceptAccessView.as_view(), name='accept_access'),
    path('superuser/', SuperuserDashboardView.as_view(), name='superuser_dashboard'),
    path('superuser/user/<int:user_id>/', SuperuserUserFilesView.as_view(), name='superuser_user_files'),
    path('view/<int:file_id>/', ViewFileView.as_view(), name='view_file'),
    path('request-access/file/<int:file_id>/', RequestAccessToFileView.as_view(), name='request_access_file'),
    path('request-access/folder/<int:folder_id>/', RequestAccessToFolderView.as_view(), name='request_access_folder'),
    path('access-requests/', OwnerAccessRequestsView.as_view(), name='owner_access_requests'),
    path('access-requests/approve/<int:request_id>/', ApproveAccessRequestView.as_view(), name='approve_access_request'),
    path('access-requests/reject/<int:request_id>/', RejectAccessRequestView.as_view(), name='reject_access_request'),
    path('share-link/file/<str:token>/', ShareLinkFileView.as_view(), name='share_link_file'),
    path('share-link/folder/<str:token>/', ShareLinkFolderView.as_view(), name='share_link_folder'),
    path('api/share-info/<str:type>/<int:id>/', ShareInfoView.as_view(), name='api_share_info'),
    path('api/share-update/<str:type>/<int:id>/', ShareUpdateView.as_view(), name='api_share_update'),
    path('api/share-add-user/<str:type>/<int:id>/', ShareAddUserView.as_view(), name='api_share_add_user'),
    path('api/share-remove-user/<str:type>/<int:id>/', ShareRemoveUserView.as_view(), name='api_share_remove_user'),
] 