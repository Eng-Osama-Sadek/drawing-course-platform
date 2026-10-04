import json
import os
import tempfile
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
    session,
    url_for,
)

# ØªØ­Ù…ÙŠÙ„ Ø§Ù„Ù…ØªØºÙŠØ±Ø§Øª Ø§Ù„Ø³Ø±ÙŠØ© Ù…Ù† Ù…Ù„Ù .env
load_dotenv()

# Ù…Ø­Ø§ÙˆÙ„Ø© Ø§Ø³ØªÙŠØ±Ø§Ø¯ Ø¯Ø§Ù„Ø© Ø§Ù„Ø±ÙØ¹ Ø¥Ù„Ù‰ Google Drive Ø¥Ø°Ø§ ÙƒØ§Ù† Ù…Ù„Ù Ø§Ù„Ø±Ø¨Ø· Ù…ÙˆØ¬ÙˆØ¯Ø§Ù‹
try:
    from drive_uploader import upload_file_to_drive

    DRIVE_ENABLED = True
except ImportError:
    DRIVE_ENABLED = False

app = Flask(__name__)

# Ù‚Ø±Ø§Ø¡Ø© Ù…ÙØªØ§Ø­ Ø§Ù„Ø£Ù…Ø§Ù† ÙˆÙ…ÙØªØ§Ø­ Gemini Ù…Ø¹ Ø§Ù„Ø­ÙØ§Ø¸ Ø¹Ù„Ù‰ Ø§Ù„Ù‚ÙŠÙ… Ø§Ù„Ø§ÙØªØ±Ø§Ø¶ÙŠØ©
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_key_for_eng_osama')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'Ø¶Ø¹_Ù…ÙØªØ§Ø­_Ø¬ÙˆØ¬Ù„_Ù‡Ù†Ø§')

# âœ… Ø§Ø³ØªØ®Ø¯Ø§Ù… /tmp Ø¹Ù„Ù‰ Vercel (Ø§Ù„Ù…Ø³Ø§Ø± Ø§Ù„ÙˆØ­ÙŠØ¯ Ø§Ù„Ù‚Ø§Ø¨Ù„ Ù„Ù„ÙƒØªØ§Ø¨Ø©)
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', tempfile.gettempdir())
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 Ù…ÙŠØ¬Ø§Ø¨Ø§ÙŠØª

# âœ… Ù„Ø§ Ù†Ø³ØªØ®Ø¯Ù… os.makedirs â€” /tmp Ù…ÙˆØ¬ÙˆØ¯ Ù…Ø³Ø¨Ù‚Ø§Ù‹

users_db = [
    {'name': 'Ø·Ø§Ù„Ø¨ ØªØ¬Ø±ÙŠØ¨ÙŠ', 'phone': '010000000', 'paid': False, 'status': 'pending'}
]

# Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ù…Ù„ÙØ§Øª Ø§Ù„Ù…Ø³Ø¬Ù„Ø© ÙˆØ§Ù„Ù…Ø±ÙÙˆØ¹Ø©
files_db = [
    {
        'name': 'Ù…Ø­Ø§Ø¶Ø±Ø©_Ø§Ù„Ù…Ù†Ø¸ÙˆØ±_Ø§Ù„Ø§ÙŠØ²ÙˆÙ…ØªØ±ÙŠ.mp4',
        'type': 'video',
        'category': 'ÙÙŠØ¯ÙŠÙˆ',
        'url': '#',
    },
    {
        'name': 'ØªÙ…Ø§Ø±ÙŠÙ†_Ø§Ù„Ù‚Ø·Ø§Ø¹Ø§Øª_ÙˆØ§Ù„ØªÙ‡Ø´ÙŠØ±.pdf',
        'type': 'pdf',
        'category': 'Ù…Ø³ØªÙ†Ø¯',
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
    is_paid = session.get('is_paid', False) or any(u.get('paid', False) for u in users_db)
    return render_template('index.html', files=files_db, is_paid=is_paid)


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
                    cat_label = 'ÙÙŠØ¯ÙŠÙˆ'
                elif cat == 'image':
                    cat_label = 'ØµÙˆØ±Ø©'
                else:
                    cat_label = 'Ù…Ø³ØªÙ†Ø¯'

                files_db.append({
                    'name': file.filename,
                    'type': cat,
                    'category': cat_label,
                    'url': drive_url if drive_url else f'/uploads/{file.filename}',
                })
                flash('ØªÙ… Ø±ÙØ¹ Ø§Ù„Ù…Ù„Ù Ø¨Ù†Ø¬Ø§Ø­!')

    return render_template('admin.html', users=users_db, files=files_db)


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
            'category': 'ÙÙŠØ¯ÙŠÙˆ Ù…Ø³Ø¬Ù„',
            'url': drive_url if drive_url else f'/uploads/{filename}',
        })
        return jsonify({'status': 'success', 'message': 'ØªÙ… Ø­ÙØ¸ Ø§Ù„ÙÙŠØ¯ÙŠÙˆ Ø¨Ù†Ø¬Ø§Ø­!'})
    return jsonify({'status': 'error', 'message': 'ÙØ´Ù„ Ø±ÙØ¹ Ø§Ù„ÙÙŠØ¯ÙŠÙˆ'}), 400


@app.route('/approve/<phone>')
def approve_user(phone):
    for user in users_db:
        if user['phone'] == phone:
            user['paid'] = True
            user['status'] = 'approved'
            session['is_paid'] = True
    flash(f'ØªÙ… ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø­Ø³Ø§Ø¨ Ù„Ù„Ø·Ø§Ù„Ø¨ ØµØ§Ø­Ø¨ Ø§Ù„Ø±Ù‚Ù… {phone}')
    return redirect(url_for('admin'))


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get('message')

    if not user_message:
        return jsonify({'reply': 'Ø¹ÙÙˆØ§Ù‹ØŒ Ù„Ù… Ø£Ø³ØªÙ„Ù… Ø£ÙŠ Ø±Ø³Ø§Ù„Ø©.'}), 400

    clean_key = GEMINI_API_KEY.strip() if GEMINI_API_KEY else ''

    if not clean_key or clean_key == 'Ø¶Ø¹_Ù…ÙØªØ§Ø­_Ø¬ÙˆØ¬Ù„_Ù‡Ù†Ø§' or any(ord(c) > 127 for c in clean_key):
        print("âš ï¸ ØªÙ†Ø¨ÙŠÙ‡: Ù…ÙØªØ§Ø­ GEMINI_API_KEY ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ ÙŠØ­ØªÙˆÙŠ Ø¹Ù„Ù‰ Ø­Ø±ÙˆÙ ØºÙŠØ± ØµØ­ÙŠØ­Ø© ÙÙŠ .env")
        return jsonify({
            'reply': 'ÙŠØ±Ø¬Ù‰ Ø¥Ø¶Ø§ÙØ© Ù…ÙØªØ§Ø­ GEMINI_API_KEY Ø§Ù„Ø­Ù‚ÙŠÙ‚ÙŠ Ø§Ù„Ø®Ø§Øµ Ø¨Ùƒ ÙÙŠ Ù…Ù„Ù .env Ø­ØªÙ‰ ÙŠØ³ØªØ·ÙŠØ¹ Ø§Ù„Ù…Ø³Ø§Ø¹Ø¯ Ø§Ù„Ø°ÙƒÙŠ Ø§Ù„Ø¥Ø¬Ø§Ø¨Ø©.'
        }), 400

    encoded_key = quote(clean_key)

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={encoded_key}'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{
                'text': (
                    'Ø£Ù†Øª Ù…Ø³Ø§Ø¹Ø¯ Ø°ÙƒÙŠ ÙÙŠ Ù…Ù†ØµØ© Ù„ØªØ¹Ù„ÙŠÙ… Ø§Ù„Ø±Ø³Ù… Ø§Ù„Ù‡Ù†Ø¯Ø³ÙŠ Ù„Ù„Ù…Ù‡Ù†Ø¯Ø³ Ø£Ø³Ø§Ù…Ø©'
                    ' ØµØ§Ø¯Ù‚.\nØ£Ø¬Ø¨ Ø¹Ù„Ù‰ Ù‡Ø°Ø§ Ø§Ù„Ø³Ø¤Ø§Ù„ Ø¨Ø§Ø®ØªØµØ§Ø± ÙˆØ§Ø­ØªØ±Ø§ÙÙŠØ© ÙˆØ¨Ø§Ù„Ù„ØºØ©'
                    f' Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©:\nØ§Ù„Ø³Ø¤Ø§Ù„: {user_message}'
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
        print(f"âŒ Ø®Ø·Ø£ Ù…Ù† Ø³ÙŠØ±ÙØ± Ø¬ÙˆØ¬Ù„ (HTTP {http_err.code}): {error_body}")
        if http_err.code == 404:
            return jsonify({
                'reply': 'Ø®Ø·Ø£ 404: Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ Ø£Ù† Ø§Ù„Ù…ÙØªØ§Ø­ ÙŠÙ†Ù‚ØµÙ‡ ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø®Ø¯Ù…Ø© Ù…Ù† Google AI Studio.'
            }), 500
        return jsonify({
            'reply': f'Ø­Ø¯Ø« Ø®Ø·Ø£ Ù…Ù† Ø³ÙŠØ±ÙØ± Ø¬ÙˆØ¬Ù„ (Ø±Ù…Ø² {http_err.code}). ØªØ£ÙƒØ¯ Ù…Ù† ØµØ­Ø© Ù…ÙØªØ§Ø­ Ø§Ù„Ù€ API.'
        }), 500

    except Exception as e:
        print(f"âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø§ØªØµØ§Ù„ Ø¨Ø§Ù„Ù…Ø³Ø§Ø¹Ø¯ Ø§Ù„Ø°ÙƒÙŠ: {e}")
        return jsonify({'reply': 'Ø¹Ø°Ø±Ø§Ù‹ØŒ Ø­Ø¯Ø« Ø®Ø·Ø£ Ø£Ø«Ù†Ø§Ø¡ Ø§Ù„Ø§ØªØµØ§Ù„ Ø¨Ø§Ù„Ù…Ø³Ø§Ø¹Ø¯ Ø§Ù„Ø°ÙƒÙŠ.'}), 500


# âœ… Ù„Ø§ Ù†Ø­ØªØ§Ø¬ app.run() Ø¹Ù„Ù‰ Vercel â€” Vercel ÙŠØ³ØªØ¯Ø¹ÙŠ app Ù…Ø¨Ø§Ø´Ø±Ø©