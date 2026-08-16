import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

# تحميل المتغيرات السرية من ملف .env
load_dotenv()

# محاولة استيراد دالة الرفع إلى Google Drive إذا كان ملف الربط موجوداً
try:
    from drive_uploader import upload_file_to_drive

    DRIVE_ENABLED = True
except ImportError:
    DRIVE_ENABLED = False

app = Flask(__name__)

# قراءة مفتاح الأمان ومفتاح Gemini مع الحفاظ على القيم الافتراضية
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key_for_eng_osama')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'ضع_مفتاح_جوجل_هنا')

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 ميجابايت

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

users_db = [
    {'name': 'طالب تجريبي', 'phone': '010000000', 'paid': False, 'status': 'pending'}
]

# قائمة الملفات المسجلة والمرفوعة
files_db = [
    {
        'name': 'محاضرة_المنظور_الايزومتري.mp4',
        'type': 'video',
        'category': 'فيديو',
        'url': '#',
    },
    {
        'name': 'تمارين_القطاعات_والتهشير.pdf',
        'type': 'pdf',
        'category': 'مستند',
        'url': '#',
    },
]


def get_file_category(filename):
    ext = filename.split('.')[-1].lower()
    if ext in ['mp4', 'webm', 'avi', 'mov']:
        return 'video'
    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
        return 'image'
    elif ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx']:
        return 'doc'
    return 'other'


@app.route('/')
def index():
    return render_template('index.html', files=files_db)


# مسار استعراض وتحميل الملفات المرفوعة محلياً
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                drive_url = None
                if DRIVE_ENABLED:
                    try:
                        drive_result = upload_file_to_drive(filepath)
                        if drive_result.get('status') == 'success':
                            drive_url = drive_result.get('web_view_link')
                            if os.path.exists(filepath):
                                os.remove(filepath)
                    except Exception as e:
                        print(f'Drive Upload Error: {e}')

                cat = get_file_category(file.filename)
                if cat == 'video':
                    cat_label = 'فيديو'
                elif cat == 'image':
                    cat_label = 'صورة'
                else:
                    cat_label = 'مستند'

                files_db.append({
                    'name': file.filename,
                    'type': cat,
                    'category': cat_label,
                    'url': drive_url if drive_url else f'/uploads/{file.filename}',
                })
                flash('تم رفع الملف بنجاح!')

    return render_template('admin.html', users=users_db, files=files_db)


# استقبال فيديو الكاميرا أو الشاشة المباشر من لوحة التحكم
@app.route('/upload_recorded_video', methods=['POST'])
def upload_recorded_video():
    if 'video' in request.files:
        video_file = request.files['video']
        filename = f'RECORDED_LECTURE_{len(files_db) + 1}.webm'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(filepath)

        drive_url = None
        if DRIVE_ENABLED:
            try:
                drive_result = upload_file_to_drive(filepath)
                if drive_result.get('status') == 'success':
                    drive_url = drive_result.get('web_view_link')
                    if os.path.exists(filepath):
                        os.remove(filepath)
            except Exception as e:
                print(f'Drive Error: {e}')

        files_db.append({
            'name': filename,
            'type': 'video',
            'category': 'فيديو مسجل',
            'url': drive_url if drive_url else f'/uploads/{filename}',
        })
        return jsonify({'status': 'success', 'message': 'تم حفظ الفيديو بنجاح!'})
    return jsonify({'status': 'error', 'message': 'فشل رفع الفيديو'}), 400


@app.route('/approve/<phone>')
def approve_user(phone):
    for user in users_db:
        if user['phone'] == phone:
            user['paid'] = True
            user['status'] = 'approved'
    flash(f'تم تفعيل الحساب للطالب صاحب الرقم {phone}')
    return redirect(url_for('admin'))


# ==========================================
#  خاصية المساعد الذكي (Gemini Chat API)
# ==========================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message')

    if not user_message:
        return jsonify({'reply': 'عفواً، لم أستلم أي رسالة.'}), 400

    clean_key = GEMINI_API_KEY.strip() if GEMINI_API_KEY else ''

    # 1. التحقق من صحة مفتاح الـ API وعدم وجود الحروف الافتراضية بالعربية
    if not clean_key or clean_key == 'ضع_مفتاح_جوجل_هنا' or any(ord(c) > 127 for c in clean_key):
        print("⚠️ تنبيه: مفتاح GEMINI_API_KEY غير موجود أو يحتوي على حروف غير صحيحة في .env")
        return jsonify({
            'reply': 'يرجى إضافة مفتاح GEMINI_API_KEY الحقيقي الخاص بك في ملف .env حتى يستطيع المساعد الذكي الإجابة.'
        }), 400

    # 2. ترميز المفتاح بأمان لتجنب أخطاء الـ URL
    encoded_key = quote(clean_key)
    
    # تم التحديث إلى gemini-2.5-flash المتوافق مع حسابك المفعّل
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={encoded_key}'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{
                'text': (
                    'أنت مساعد ذكي في منصة لتعليم الرسم الهندسي للمهندس أسامة'
                    ' صادق.\nأجب على هذا السؤال باختصار واحترافية وباللغة'
                    f' العربية:\nالسؤال: {user_message}'
                )
            }]
        }]
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply_text = result['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'reply': reply_text})

    except urllib.error.HTTPError as http_err:
        error_body = http_err.read().decode('utf-8')
        print(f"❌ خطأ من سيرفر جوجل (HTTP {http_err.code}): {error_body}")
        if http_err.code == 404:
            return jsonify({
                'reply': 'خطأ 404: النموذج غير موجود أو أن المفتاح ينقصه تفعيل الخدمة من Google AI Studio.'
            }), 500
        return jsonify({
            'reply': f'حدث خطأ من سيرفر جوجل (رمز {http_err.code}). تأكد من صحة مفتاح الـ API.'
        }), 500

    except Exception as e:
        print(f"❌ خطأ في الاتصال بالمساعد الذكي: {e}")
        return jsonify({'reply': 'عذراً، حدث خطأ أثناء الاتصال بالمساعد الذكي.'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)