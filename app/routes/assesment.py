# app/routes/assesment.py

from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from app.utils.jwt_utils import jwt_required, get_jwt_identity
import logging

assesment_bp = Blueprint('assesment', __name__)

@assesment_bp.route('/assesment', methods=['POST'])
@jwt_required()
def save_assesment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Data kosong'}), 400

        user_id = get_jwt_identity()
        data['user_id'] = ObjectId(user_id)
        data['created_at'] = datetime.utcnow()

        # Simpan ke koleksi assesments
        current_app.db.assesments.insert_one(data)

        # Simpan juga ke koleksi history
        history_entry = {
            'user_id': ObjectId(user_id),
            'label': f"Assesmen risiko: {data.get('tingkat_keparahan', '-')}",
            'timestamp': datetime.utcnow()
        }
        current_app.db.history.insert_one(history_entry)

        return jsonify({'status': 'success', 'message': 'Data berhasil disimpan'}), 201

    except Exception as e:
        logging.exception("Error menyimpan assesment:")
        return jsonify({'status': 'error', 'message': f'Gagal menyimpan data: {str(e)}'}), 500
