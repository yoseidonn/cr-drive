document.addEventListener('DOMContentLoaded', function() {
  var fabBtn = document.getElementById('fabMenuBtn');
  var fabMenu = document.getElementById('fabMenu');
  if (fabBtn && fabMenu) {
    fabBtn.addEventListener('click', function() {
      fabMenu.style.display = fabMenu.style.display === 'none' ? 'block' : 'none';
    });
    document.addEventListener('click', function(e) {
      if (!fabBtn.contains(e.target) && !fabMenu.contains(e.target)) {
        fabMenu.style.display = 'none';
      }
    });
  }
  if (typeof show_upload_modal !== 'undefined' && show_upload_modal) {
    var uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
    uploadModal.show();
  }
  if (typeof show_folder_modal !== 'undefined' && show_folder_modal) {
    var folderModal = new bootstrap.Modal(document.getElementById('folderModal'));
    folderModal.show();
  }
  if (typeof show_rename_modal !== 'undefined' && show_rename_modal) {
    var renameModal = new bootstrap.Modal(document.getElementById('renameModal'));
    renameModal.show();
  }
  if (typeof show_move_modal !== 'undefined' && show_move_modal) {
    var moveModal = new bootstrap.Modal(document.getElementById('moveModal'));
    moveModal.show();
  }
  if (typeof show_remove_modal !== 'undefined' && show_remove_modal) {
    var removeModal = new bootstrap.Modal(document.getElementById('removeModal'));
    removeModal.show();
  }

  // Drag-and-drop logic
  var dropArea = document.getElementById('dropArea');
  var fileInput = document.getElementById('fileInput');
  var selectedFilesList = document.getElementById('selectedFilesList');
  if (dropArea && fileInput) {
    dropArea.addEventListener('click', function() { fileInput.click(); });
    dropArea.addEventListener('dragover', function(e) { e.preventDefault(); dropArea.classList.add('bg-info'); });
    dropArea.addEventListener('dragleave', function(e) { e.preventDefault(); dropArea.classList.remove('bg-info'); });
    dropArea.addEventListener('drop', function(e) {
      e.preventDefault();
      dropArea.classList.remove('bg-info');
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        updateSelectedFilesList();
      }
    });
    fileInput.addEventListener('change', function() {
      updateSelectedFilesList();
    });
  }
  function updateSelectedFilesList() {
    if (fileInput.files.length) {
      let html = '<ul class="list-group">';
      for (let i = 0; i < fileInput.files.length; i++) {
        html += '<li class="list-group-item">' + fileInput.files[i].name + ' <span class="text-muted small">(' + formatFileSize(fileInput.files[i].size) + ')</span></li>';
      }
      html += '</ul>';
      selectedFilesList.innerHTML = html;
    } else {
      selectedFilesList.innerHTML = '';
    }
  }

  // Upload progress bar logic (multiple files)
  var uploadForm = document.getElementById('uploadForm');
  var progressBar = document.getElementById('uploadProgressBar');
  var progress = progressBar ? progressBar.querySelector('.progress-bar') : null;
  var uploadStatus = document.getElementById('uploadStatus');
  if (uploadForm && progressBar && progress) {
    uploadForm.addEventListener('submit', function(e) {
      if (fileInput.files.length === 0) {
        uploadStatus.innerHTML = '<div class="alert alert-danger">Please select files to upload.</div>';
        e.preventDefault();
        return;
      }
      e.preventDefault();
      let files = fileInput.files;
      let total = files.length;
      let uploaded = 0;
      function uploadNext() {
        if (uploaded >= total) {
          progress.style.width = '100%';
          progress.innerText = '100%';
          uploadStatus.innerHTML = '<div class="alert alert-success">All files uploaded! Refreshing...</div>';
          setTimeout(function() { window.location.reload(); }, 1000);
          return;
        }
        let formData = new FormData();
        formData.append('upload_file', '1');
        formData.append('file', files[uploaded]);
        formData.append('csrfmiddlewaretoken', window.csrf_token || '');
        var xhr = new XMLHttpRequest();
        xhr.open('POST', window.location.href);
        xhr.upload.onprogress = function(e) {
          if (e.lengthComputable) {
            var percent = Math.round((e.loaded / e.total) * 100);
            progressBar.classList.remove('d-none');
            progress.style.width = percent + '%';
            progress.innerText = percent + '% (' + (uploaded+1) + '/' + total + ')';
          }
        };
        xhr.onload = function() {
          if (xhr.status === 200) {
            let resp = {};
            try { resp = JSON.parse(xhr.responseText); } catch (e) {}
            if (resp.status === 'success') {
              uploaded++;
              uploadNext();
            } else {
              let msg = resp.message || 'Upload failed.';
              uploadStatus.innerHTML = '<div class="alert alert-danger">' + msg + '</div>';
              progressBar.classList.add('d-none');
            }
          } else {
            let msg = 'Upload failed: ' + xhr.statusText;
            if (xhr.responseText) {
              msg += '<br>' + xhr.responseText;
            }
            uploadStatus.innerHTML = '<div class="alert alert-danger">' + msg + '</div>';
            progressBar.classList.add('d-none');
          }
        };
        xhr.onerror = function() {
          uploadStatus.innerHTML = '<div class="alert alert-danger">Upload failed. Please try again.</div>';
        };
        xhr.send(formData);
      }
      uploadNext();
    });
  }

  // Context menu logic
  let contextMenu = document.getElementById('contextMenu');
  let currentTargetType = null;
  let currentTargetId = null;
  document.querySelectorAll('.explorer-item').forEach(function(item) {
    item.addEventListener('contextmenu', function(e) {
      e.preventDefault();
      currentTargetType = item.getAttribute('data-type');
      currentTargetId = item.getAttribute('data-id');
      contextMenu.style.display = 'block';
      contextMenu.style.left = e.pageX + 'px';
      contextMenu.style.top = e.pageY + 'px';
    });
  });
  document.addEventListener('click', function(e) {
    if (!contextMenu.contains(e.target)) {
      contextMenu.style.display = 'none';
    }
  });
  // Add "View" action for files
  let viewMenuBtn = document.createElement('button');
  viewMenuBtn.className = 'dropdown-item';
  viewMenuBtn.innerHTML = '<i class="bi bi-eye"></i> View';
  contextMenu.insertBefore(viewMenuBtn, contextMenu.firstChild);
  viewMenuBtn.onclick = function() {
    if (currentTargetType === 'file') {
      window.open('/storage/view/' + currentTargetId + '/', '_blank');
    }
    contextMenu.style.display = 'none';
  };
  document.getElementById('renameBtn').onclick = function() {
    document.getElementById('renameTargetType').value = currentTargetType;
    document.getElementById('renameTargetId').value = currentTargetId;
    var renameModal = new bootstrap.Modal(document.getElementById('renameModal'));
    renameModal.show();
    contextMenu.style.display = 'none';
  };
  document.getElementById('moveBtn').onclick = function() {
    document.getElementById('moveTargetType').value = currentTargetType;
    document.getElementById('moveTargetId').value = currentTargetId;
    var moveModal = new bootstrap.Modal(document.getElementById('moveModal'));
    moveModal.show();
    contextMenu.style.display = 'none';
  };
  document.getElementById('removeBtn').onclick = function() {
    document.getElementById('removeTargetType').value = currentTargetType;
    document.getElementById('removeTargetId').value = currentTargetId;
    var removeModal = new bootstrap.Modal(document.getElementById('removeModal'));
    removeModal.show();
    contextMenu.style.display = 'none';
  };
  document.getElementById('shareBtn').onclick = function() {
    if (currentTargetType && currentTargetId) {
      // Find the name for the modal (from DOM)
      let name = '';
      let item = document.querySelector('.explorer-item[data-type="' + currentTargetType + '"][data-id="' + currentTargetId + '"]');
      if (item) {
        let nameElem = item.querySelector('.card-body .mt-2') || item.querySelector('a.flex-grow-1') || item.querySelector('.mt-2.small');
        if (nameElem) name = nameElem.textContent.trim();
      }
      openShareModal(currentTargetType, currentTargetId, name);
    }
    contextMenu.style.display = 'none';
  };

  // Drag-and-drop move logic (basic visual feedback)
  let draggedItem = null;
  document.querySelectorAll('.explorer-item').forEach(function(item) {
    item.setAttribute('draggable', true);
    item.addEventListener('dragstart', function(e) {
      draggedItem = item;
      e.dataTransfer.effectAllowed = 'move';
    });
    item.addEventListener('dragover', function(e) {
      e.preventDefault();
      item.classList.add('bg-info');
    });
    item.addEventListener('dragleave', function(e) {
      item.classList.remove('bg-info');
    });
    item.addEventListener('drop', function(e) {
      e.preventDefault();
      item.classList.remove('bg-info');
      if (draggedItem && item.getAttribute('data-type') === 'folder') {
        // Open move modal with dragged item as target and this folder as destination
        currentTargetType = draggedItem.getAttribute('data-type');
        currentTargetId = draggedItem.getAttribute('data-id');
        document.getElementById('moveTargetType').value = currentTargetType;
        document.getElementById('moveTargetId').value = currentTargetId;
        document.querySelector('#moveModal select').value = item.getAttribute('data-id');
        var moveModal = new bootstrap.Modal(document.getElementById('moveModal'));
        moveModal.show();
      }
    });
  });

  // Add a "View" button for each file and double-click to view
  document.querySelectorAll('.explorer-item[data-type="file"]').forEach(function(item) {
    let fileId = item.getAttribute('data-id');
    let viewBtn = document.createElement('a');
    viewBtn.href = '/storage/view/' + fileId + '/';
    viewBtn.className = 'btn btn-sm btn-outline-info ms-1';
    viewBtn.innerHTML = '<i class="bi bi-eye"></i> View';
    let cardBody = item.querySelector('.card-body .mt-1') || item.querySelector('.justify-content-between');
    if (cardBody) cardBody.appendChild(viewBtn);
    // Double-click to view
    item.addEventListener('dblclick', function(e) {
      window.open('/storage/view/' + fileId + '/', '_blank');
    });
  });

  // Update file size display in file/folder lists
  function formatFileSize(size) {
    if (size >= 1024*1024) {
      return (size/1024/1024).toFixed(2) + ' MB';
    } else if (size >= 1024) {
      return (size/1024).toFixed(2) + ' KB';
    } else {
      return size + ' bytes';
    }
  }
  document.querySelectorAll('.file-size').forEach(function(span) {
    let size = parseInt(span.getAttribute('data-size'));
    span.innerText = '(' + formatFileSize(size) + ')';
  });

  window.triggerRemoveModal = function(id, type) {
    document.getElementById('removeTargetType').value = type;
    document.getElementById('removeTargetId').value = id;
    var removeModal = new bootstrap.Modal(document.getElementById('removeModal'));
    removeModal.show();
  };

  // --- SHARE MODAL AJAX LOGIC ---
  window.openShareModal = function(type, id, name) {
    document.getElementById('shareModalItemName').textContent = name;
    const shareLinkInput = document.getElementById('shareLinkInput');
    const shareVisibilitySelect = document.getElementById('shareVisibilitySelect');
    const sharedUsersList = document.getElementById('sharedUsersList');
    const addShareUserForm = document.getElementById('addShareUserForm');
    const shareModalFeedback = document.getElementById('shareModalFeedback');
    const shareUsernameInput = document.getElementById('shareUsernameInput');
    const shareAccessLevelSelect = document.getElementById('shareAccessLevelSelect');

    // Clear feedback and user input
    shareModalFeedback.innerHTML = '';
    shareUsernameInput.value = '';
    shareAccessLevelSelect.value = 'read';

    // Fetch share info
    fetch(`/storage/api/share-info/${type}/${id}/`, {credentials: 'same-origin'})
      .then(r => r.json())
      .then(data => {
        shareLinkInput.value = data.share_link;
        shareVisibilitySelect.value = data.visibility;
        shareVisibilitySelect.disabled = !data.is_owner;
        // Populate shared users
        sharedUsersList.innerHTML = '';
        if (data.shared_users.length === 0) {
          sharedUsersList.innerHTML = '<li class="list-group-item text-muted">No users</li>';
        } else {
          data.shared_users.forEach(function(u) {
            let li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `<span>${u.user__username} <span class='badge bg-light text-dark ms-2'>${u.access_level}</span></span>`;
            if (data.is_owner) {
              let btn = document.createElement('button');
              btn.className = 'btn btn-sm btn-outline-danger';
              btn.innerHTML = '<i class="bi bi-x"></i>';
              btn.onclick = function() {
                if (!confirm(`Remove ${u.user__username}?`)) return;
                fetch(`/storage/api/share-remove-user/${type}/${id}/`, {
                  method: 'POST',
                  headers: {'X-CSRFToken': window.csrf_token},
                  body: new URLSearchParams({username: u.user__username})
                })
                .then(r => r.json())
                .then(resp => {
                  if (resp.status === 'success') {
                    openShareModal(type, id, name); // reload
                  } else {
                    shareModalFeedback.innerHTML = `<div class='alert alert-danger'>${resp.message || 'Error'}</div>`;
                  }
                });
              };
              li.appendChild(btn);
            }
            sharedUsersList.appendChild(li);
          });
        }
        // Enable/disable add user form
        addShareUserForm.querySelector('button[type="submit"]').disabled = !data.is_owner;
        shareUsernameInput.disabled = !data.is_owner;
        shareAccessLevelSelect.disabled = !data.is_owner;
      });

    // Show modal
    var shareModal = new bootstrap.Modal(document.getElementById('shareModal'));
    shareModal.show();

    // Visibility change
    shareVisibilitySelect.onchange = function() {
      if (!shareVisibilitySelect.disabled) {
        fetch(`/storage/api/share-update/${type}/${id}/`, {
          method: 'POST',
          headers: {'X-CSRFToken': window.csrf_token},
          body: new URLSearchParams({visibility: shareVisibilitySelect.value})
        })
        .then(r => r.json())
        .then(resp => {
          if (resp.status === 'success') {
            shareModalFeedback.innerHTML = `<div class='alert alert-success'>Visibility updated.</div>`;
          } else {
            shareModalFeedback.innerHTML = `<div class='alert alert-danger'>${resp.message || 'Error'}</div>`;
          }
        });
      }
    };

    // Add user form submit
    addShareUserForm.onsubmit = function(e) {
      e.preventDefault();
      if (!shareUsernameInput.value.trim()) return;
      fetch(`/storage/api/share-add-user/${type}/${id}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': window.csrf_token},
        body: new URLSearchParams({
          username: shareUsernameInput.value.trim(),
          access_level: shareAccessLevelSelect.value
        })
      })
      .then(r => r.json())
      .then(resp => {
        if (resp.status === 'success') {
          shareModalFeedback.innerHTML = `<div class='alert alert-success'>User added.</div>`;
          openShareModal(type, id, name); // reload
        } else {
          shareModalFeedback.innerHTML = `<div class='alert alert-danger'>${resp.message || 'Error'}</div>`;
        }
      });
    };
  };
}); 