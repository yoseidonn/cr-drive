# CR-Drive: Secure Cloud Drive System

CR-Drive is a modern, secure cloud storage system built with Django. It features user authentication, encrypted file storage, granular sharing and permissions, and a beautiful, mobile-friendly UI powered by Bootstrap 5.

---

## Features

- **User Authentication**: Register, log in, and manage your files securely.
- **Encrypted File Storage**: All files are encrypted at rest using Fernet encryption.
- **Granular Sharing**: Share files and folders with other users, set access levels, and generate unique share links.
- **Visibility Modes**: Set files/folders as `private`, `public`, or `ask` (request access).
- **Access Requests**: Users can request access to restricted files/folders; owners can approve or reject requests.
- **Superuser Dashboard**: Admins can view and manage all users, files, and folders.
- **Modern UI**: Responsive, mobile-friendly interface with drag-and-drop, context menus, and modals.
- **AJAX-Powered**: Live updates for sharing, permissions, and notifications.
- **Quota Management**: Per-user and total storage quotas enforced.

---

## Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd cr-drive
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv env
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
- Copy `.env.example` to `.env` and fill in your secrets (Django secret key, database URL, etc).

### 5. Apply Migrations
```bash
cd cr_drive_container
python manage.py migrate
```

### 6. Create a Superuser
```bash
python manage.py createsuperuser
```

### 7. Run the Development Server
```bash
python manage.py runserver
```

Visit [http://localhost:8000/](http://localhost:8000/) in your browser.

---

## Usage

- **Upload Files**: Drag and drop or use the upload button.
- **Create Folders**: Organize your files in folders.
- **Share**: Right-click or use the share button to generate share links or add users.
- **Set Visibility**: Choose between `private`, `public`, or `ask` for each file/folder.
- **Request Access**: If you encounter an "ask" item, request access from the owner.
- **Notifications**: Owners see badges for pending access requests.
- **Superuser**: Log in as superuser to access the admin dashboard.

---

## Development

- **Frontend**: All custom JS is in `cr_drive_container/static/js/drive.js`. Styles use Bootstrap 5.
- **Backend**: Main apps are `accounts`, `storage`, `sharing`, and `pages`.
- **Database**: Uses PostgreSQL (configure in `.env`).
- **Encryption**: Files are encrypted/decrypted transparently on upload/download.
- **Testing**: Add tests in each app's `tests.py`.

---

## Security Notes
- All file contents are encrypted at rest.
- Share links are unguessable tokens.
- Private items cannot be accessed or leaked via share links.
- All secrets and sensitive settings must be in `.env` (never commit secrets!).

---

## License
MIT License. See `LICENSE` file for details.

---

## Credits
- Built with [Django](https://www.djangoproject.com/), [Bootstrap 5](https://getbootstrap.com/), and [cryptography](https://cryptography.io/). 