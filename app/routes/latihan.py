from flask import Blueprint, jsonify, current_app

latihan_bp = Blueprint('latihan', __name__)

@latihan_bp.route('/latihan', methods=['GET'])
def get_latihan():
    try:
        latihan = list(current_app.db.latihan.find({}, {"_id": 0, "title": 1, "subtitle": 1, "youtube_link": 1}))
        return jsonify({"status": "success", "data": latihan}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
