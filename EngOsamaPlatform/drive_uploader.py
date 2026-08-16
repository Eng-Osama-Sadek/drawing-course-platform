# drive_uploader.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


def upload_file_to_drive(file_path):
  try:
    gauth = GoogleAuth()
    # يحاول تحميل الجلسة المحفوظة أو فتح المتصفح للتسجيل أول مرة
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    filename = file_path.split('/')[-1].split('\\')[-1]
    file_drive = drive.CreateFile({'title': filename})
    file_drive.SetContentFile(file_path)
    file_drive.Upload()

    # جعل الملف متاح للمشاهدة عبر الرابط
    file_drive.InsertPermission({
        'type': 'anyone',
        'value': 'anyone',
        'role': 'reader',
    })

    return {'status': 'success', 'web_view_link': file_drive['alternateLink']}
  except Exception as e:
    print(f'Drive error: {e}')
    return {'status': 'error', 'message': str(e)}