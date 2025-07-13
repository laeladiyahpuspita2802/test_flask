from flask import Blueprint, jsonify, current_app, request

gerakan_bp = Blueprint('gerakan', __name__)

@gerakan_bp.route('/gerakan', methods=['GET'])
def get_latihan():
    tingkat = request.args.get('tingkat', 'aman')  # default aman

    try:
        gerakan_collection = current_app.db.latihan_dataset

        if tingkat == 'aman':
            # Ambil semua
            gerakan = list(gerakan_collection.find({}, {"_id": 0}))
        elif tingkat == 'sedang':
            gerakan = []
            kategori = ['Glute Strengthening', 'Pelvic Floor', 'Kegel', 'Pelvic Stretches']
            for k in kategori:
                data = list(gerakan_collection.find({'kategori': k}, {"_id": 0}).limit(4))
                gerakan.extend(data)
        elif tingkat == 'berat':
            # Untuk 'berat', kosongkan
            return jsonify({"status": "success", "data": []}), 200
        else:
            return jsonify({"status": "error", "message": "Tingkat tidak valid"}), 400

        return jsonify({"status": "success", "data": gerakan}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
