from flask import Blueprint, jsonify, current_app

article_bp = Blueprint('articles', __name__)

@article_bp.route('/articles', methods=['GET'])
def get_articles():
    try:
        articles = list(current_app.db.article.find({}, {"_id": 0, "title": 1, "isi": 1}))
        return jsonify({"status": "success", "data": articles}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
