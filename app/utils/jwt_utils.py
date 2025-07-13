# app/utils/jwt_utils.py

import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g

def generate_jwt(user_id, exp_minutes=60):
    payload = {
        'user_id': str(user_id),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=exp_minutes)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def jwt_required():
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'status': 'fail', 'message': 'Token tidak ditemukan'}), 401

            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
                g.user_id = payload['user_id']
            except jwt.ExpiredSignatureError:
                return jsonify({'status': 'fail', 'message': 'Token kadaluarsa'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'status': 'fail', 'message': 'Token tidak valid'}), 401

            return f(*args, **kwargs)
        return decorated
    return wrapper

def get_jwt_identity():
    return getattr(g, 'user_id', None)
