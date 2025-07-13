import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, session,jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.jwt_utils import generate_jwt, jwt_required, get_jwt_identity
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from bson import ObjectId
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import smtplib, ssl
import random
from dotenv import load_dotenv
from datetime import datetime,  timedelta

load_dotenv()

auth_bp = Blueprint('auth', __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

# Fungsi generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Fungsi kirim email
def send_otp_email(to_email, otp):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    message = f"Subject: Verifikasi Email Anda\n\nKode OTP Anda adalah: {otp}"

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=context)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message)
        
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    users_collection = current_app.db.users
    if request.method == 'GET':
        return render_template('login.html')

    if request.is_json:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"status": "fail", "message": "Username dan password wajib diisi"}), 400

        user = users_collection.find_one({"$or": [{"username": username}, {"email": username}]})
        if user and user.get("login_with") != "google" and check_password_hash(user.get("password", ""), password):
            token = generate_jwt(str(user["_id"]))
            return jsonify({"status": "success", "message": "Login berhasil", "token": token}), 200

        return jsonify({"status": "fail", "message": "Username atau password salah"}), 401

    # Handle form login
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash("Username dan password wajib diisi", "error")
        return redirect(url_for('auth.login'))

    user = users_collection.find_one({"$or": [{"username": username}, {"email": username}]})
    if user and user.get("login_with") != "google" and check_password_hash(user.get("password", ""), password):
        session['username'] = user['username']
        session['email'] = user['email']
        session['user_id'] = str(user['_id'])
        return redirect(url_for('dashboard.dashboard'))

    flash('Username/email atau password salah', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login/google', methods=['POST'])
def login_google():
    users_collection = current_app.db.users
    data = request.json
    email = data.get('email')
    id_token_str = data.get('id_token')

    if not email or not id_token_str:
        return jsonify({'status': 'error', 'message': 'Data tidak lengkap'}), 400

    try:
        id_info = id_token.verify_oauth2_token(id_token_str, google_requests.Request())
        if id_info['email'] != email:
            return jsonify({'status': 'error', 'message': 'Email tidak cocok'}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            new_user = {
                "username": id_info.get("name"),
                "email": email,
                "profile_picture": id_info.get("picture"),
                "login_with": "google"
            }
            result = users_collection.insert_one(new_user)
            user_id = result.inserted_id
        else:
            user_id = user["_id"]

        token = generate_jwt(str(user_id))
        return jsonify({'status': 'success', 'token': token}), 200

    except ValueError:
        return jsonify({'status': 'error', 'message': 'Token Google tidak valid'}), 401

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    users_collection = current_app.db.users

    if request.method == 'GET':
        return render_template('register.html')

    if request.is_json:
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if not all([username, email, password, confirm_password]):
            return jsonify({"status": "fail", "message": "Semua field wajib diisi"}), 400

        if password != confirm_password:
            return jsonify({"status": "fail", "message": "Password tidak cocok"}), 400
        
        if users_collection.find_one({"email": email}):
            return jsonify({"status": "fail", "message": "Email sudah terdaftar"}), 400

        hashed_pw = generate_password_hash(password)
        otp_code = generate_otp()

        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_pw,
            "verified": False,
            "otp_code": otp_code,
            "otp_created_at": datetime.utcnow(),
        })
        try:
            send_otp_email(email, otp_code)
        except Exception as e:
            return jsonify({"status": "fail", "message": f"Gagal mengirim email: {str(e)}"}), 500

        return jsonify({"status": "success","message": "OTP dikirim ke email Anda","email": email}), 201

    # Form Register
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not username or not email or not password:
        flash("Semua field wajib diisi", "error")
        return redirect(url_for("auth.register"))

    if users_collection.find_one({"email": email}):
        flash("Email sudah terdaftar", "error")
        return redirect(url_for("auth.register"))

    hashed_pw = generate_password_hash(password)
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_pw,
        "register_with": "admin",
    })

    session['username'] = username
    session['email'] = email
    session['user_id'] = str(users_collection.find_one({"email": email})["_id"])
    return redirect(url_for('dashboard.dashboard'))

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    user = current_app.db.users.find_one({"email": email})

    if not user or user.get("otp_code") != otp:
        return jsonify({"status": "fail", "message": "OTP tidak valid"}), 400

    otp_time = user.get("otp_created_at")
    if not otp_time or datetime.utcnow() - otp_time > timedelta(minutes=10):
        return jsonify({"status": "fail", "message": "OTP sudah kadaluarsa"}), 400

    current_app.db.users.update_one(
        {"email": email},
        {"$set": {"verified": True}, "$unset": {"otp_code": "", "otp_created_at": ""}}
    )
    return jsonify({"status": "success", "message": "Email berhasil diverifikasi"}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    users_collection = current_app.db.users
    data = request.get_json()
    email = data.get("email")

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"status": "fail", "message": "Email tidak ditemukan"}), 404

    otp = generate_otp()
    users_collection.update_one({"_id": user["_id"]},{"$set": {"otp": otp,"otp_created_at": datetime.utcnow()}})
    send_otp_email(email, otp)

    return jsonify({"status": "success", "message": "OTP berhasil dikirim ke email"}), 200

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    users_collection = current_app.db.users
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    user = users_collection.find_one({"email": email})
    if not user or user.get("otp") != otp:
        return jsonify({"status": "fail", "message": "OTP tidak valid"}), 400

    if datetime.utcnow() > user.get("otp_created_at", datetime.utcnow()) + timedelta(minutes=5):
        return jsonify({"status": "fail", "message": "OTP telah kedaluwarsa"}), 400

    # ✅ Tambahkan response success
    return jsonify({"status": "success", "message": "OTP valid"}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    users_collection = current_app.db.users
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if password != confirm_password:
        return jsonify({"status": "fail", "message": "Password tidak cocok"}), 400

    hashed_password = generate_password_hash(password)
    users_collection.update_one({"email": email}, {
        "$set": {"password": hashed_password},
        "$unset": {"otp": ""}
    })

    return jsonify({"status": "success", "message": "Password berhasil diubah"}), 200

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Berhasil logout', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    users_collection = current_app.db.users
    user = users_collection.find_one({'_id': ObjectId(user_id)})

    if not user:
        return jsonify({'status': 'fail', 'message': 'User tidak ditemukan'}), 404

    user['_id'] = str(user['_id'])
    user['password'] = user.get('password', '')  # Hanya untuk debugging, sebaiknya dihapus di production

    return jsonify({
        'status': 'success',
        'message': 'Profile ditemukan',
        'data': {
            'username': user.get('username'),
            'email': user.get('email'),
            'password': user.get('password')  # HATI-HATI: jangan tampilkan ini ke frontend di production
        }
    }), 200

@auth_bp.route('/api/profile/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json()

    username = data.get('username')
    email = data.get('email')

    users_collection = current_app.db.users
    user = users_collection.find_one({'_id': ObjectId(user_id)})

    if not user:
        return jsonify({'status': 'fail', 'message': 'User tidak ditemukan'}), 404

    # Cek apakah email baru sudah digunakan oleh orang lain
    if email:
        existing_email = users_collection.find_one({'email': email, '_id': {'$ne': ObjectId(user_id)}})
        if existing_email:
            return jsonify({'status': 'fail', 'message': 'Email sudah digunakan'}), 400

    update_data = {}
    if username:
        update_data['username'] = username
    if email:
        update_data['email'] = email

    if update_data:
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
        updated_user = users_collection.find_one({'_id': ObjectId(user_id)})
        return jsonify({
            'status': 'success',
            'message': 'Profile diperbarui',
            'data': {
                'username': updated_user.get('username'),
                'email': updated_user.get('email')
            }
        }), 200

    return jsonify({'status': 'fail', 'message': 'Tidak ada data untuk diperbarui'}), 400

@auth_bp.route('/api/profile/delete', methods=['DELETE'])
@jwt_required()
def delete_profile():
    user_id = get_jwt_identity()
    users_collection = current_app.db.users

    result = users_collection.delete_one({'_id': ObjectId(user_id)})
    if result.deleted_count:
        return jsonify({'status': 'success', 'message': 'Akun berhasil dihapus'}), 200
    return jsonify({'status': 'fail', 'message': 'Akun tidak ditemukan'}), 404

@auth_bp.route('/api/history', methods=['POST'])
@jwt_required()
def save_history():
    user_id = get_jwt_identity()
    data = request.get_json()

    label = data.get('label')
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())

    if not label:
        return jsonify({'status': 'fail', 'message': 'Label tidak boleh kosong'}), 400

    history_collection = current_app.db.history
    history_collection.insert_one({
        'user_id': ObjectId(user_id),
        'label': label,
        'timestamp': timestamp,
    })

    return jsonify({'status': 'success', 'message': 'Riwayat disimpan'}), 201

@auth_bp.route('/api/history', methods=['POST'])
@jwt_required()
def add_history():
    user_id = get_jwt_identity()
    data = request.get_json()

    label = data.get('label')
    if not label:
        return jsonify({'status': 'error', 'message': 'Label diperlukan'}), 400

    history_collection = current_app.db.history
    new_history = {
        'user_id': ObjectId(user_id),
        'label': label,
        'timestamp': datetime.utcnow()
    }

    history_collection.insert_one(new_history)

    return jsonify({'status': 'success', 'message': 'Riwayat berhasil ditambahkan'}), 201

@auth_bp.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    history_collection = current_app.db.history

    history = list(history_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1))

    result = []
    for item in history:
        result.append({
            'label': item.get('label', ''),
            'timestamp': item.get('timestamp', datetime.utcnow()).isoformat()
        })

    return jsonify({'status': 'success', 'data': result}), 200

@auth_bp.route('/api/history', methods=['DELETE'])
@jwt_required()
def delete_all_history():
    user_id = get_jwt_identity()
    history_collection = current_app.db.history

    result = history_collection.delete_many({'user_id': ObjectId(user_id)})

    return jsonify({
        'status': 'success',
        'message': f'{result.deleted_count} riwayat dihapus'
    }), 200

@auth_bp.route('/api/user-activity', methods=['POST'])
@jwt_required()
def add_user_activity():
    user_id = get_jwt_identity()
    data = request.get_json()

    action = data.get('action')
    if not action:
        return jsonify({'status': 'error', 'message': 'Aksi diperlukan'}), 400

    activity_collection = current_app.db.user_activity
    activity = {
        'user_id': ObjectId(user_id),
        'action': action,
        'timestamp': datetime.utcnow()
    }
    activity_collection.insert_one(activity)

    return jsonify({'status': 'success', 'message': 'Aktivitas dicatat'}), 201


@auth_bp.route('/api/user-activity', methods=['GET'])
@jwt_required()
def get_user_activity():
    user_id = get_jwt_identity()
    activity_collection = current_app.db.user_activity

    activities = list(activity_collection.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1))

    result = []
    for item in activities:
        result.append({
            'action': item.get('action', ''),
            'timestamp': item.get('timestamp', datetime.utcnow()).isoformat()
        })

    return jsonify({'status': 'success', 'data': result}), 200

@auth_bp.route('/api/user-activity', methods=['DELETE'])
@jwt_required()
def clear_user_activities():
    try:
        user_id = get_jwt_identity()
        activity_collection = current_app.db.user_activity
        
        # Hapus semua aktivitas milik user
        result = activity_collection.delete_many({'user_id': ObjectId(user_id)})

        return jsonify({
            'status': 'success',
            'message': f'{result.deleted_count} aktivitas dihapus'
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
