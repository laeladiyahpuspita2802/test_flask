from flask import Blueprint, render_template, redirect, request, url_for, session, current_app
from bson import ObjectId

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    users = list(current_app.db.users.find({}, {"_id": 0, "username": 1, "email": 1}))
    return render_template('dashboard.html', users=users)

@dashboard_bp.route('/users')
def users():
    all_users = current_app.db.users.find()
    return render_template('users.html', users=all_users)

@dashboard_bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = current_app.db.users.find_one({'_id': ObjectId(user_id)})
    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        current_app.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': new_username, 'email': new_email}})
        return redirect(url_for('dashboard.users'))
    return render_template('edit_user.html', user=user)

@dashboard_bp.route('/delete_user/<user_id>')
def delete_user(user_id):
    current_app.db.users.delete_one({'_id': ObjectId(user_id)})
    return redirect(url_for('dashboard.users'))
