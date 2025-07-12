from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.config['SECRET_KEY'] = '34616ef599ca22a1ac7951550dfe06ef'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------- User Model -----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    skills_offered = db.Column(db.String(200))
    skills_wanted = db.Column(db.String(200))
    availability = db.Column(db.String(100))
    location = db.Column(db.String(100))
    is_public = db.Column(db.Boolean, default=True)
    profile_photo = db.Column(db.String(300))
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)

class SkillSwapRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

# ----------------- Flask Login Setup -----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- Routes -----------------
@app.route("/")
def home():
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already registered!")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
        new_user = User(name=name, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registered successfully! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("profile"))
        flash("Invalid credentials!")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.skills_offered = request.form.get('skills_offered', '')
        current_user.skills_wanted = request.form.get('skills_wanted', '')
        current_user.availability = request.form.get('availability', '')
        current_user.location = request.form.get('location', '')
        current_user.is_public = 'is_public' in request.form
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    other_users = User.query.filter(User.id != current_user.id).all()
    incoming_requests = SkillSwapRequest.query.filter_by(receiver_id=current_user.id).all()
    outgoing_requests = SkillSwapRequest.query.filter_by(sender_id=current_user.id).all()

    return render_template('profile.html', user=current_user, other_users=other_users,
                           incoming_requests=incoming_requests, outgoing_requests=outgoing_requests)

@app.route('/swap_request/send/<int:receiver_id>')
@login_required
def send_swap_request(receiver_id):
    existing_request = SkillSwapRequest.query.filter_by(sender_id=current_user.id, receiver_id=receiver_id).first()
    if not existing_request:
        new_request = SkillSwapRequest(sender_id=current_user.id, receiver_id=receiver_id)
        db.session.add(new_request)
        db.session.commit()
        flash('Swap request sent!', 'success')
    else:
        flash('You already sent a request to this user.', 'warning')
    return redirect(url_for('profile'))

@app.route('/swap_request/accept/<int:request_id>')
@login_required
def accept_swap_request(request_id):
    req = SkillSwapRequest.query.get_or_404(request_id)
    if req.receiver_id == current_user.id:
        req.status = 'accepted'
        db.session.commit()
        flash("Request accepted!", "success")
    return redirect(url_for('profile'))

@app.route('/swap_request/reject/<int:request_id>')
@login_required
def reject_swap_request(request_id):
    req = SkillSwapRequest.query.get_or_404(request_id)
    if req.receiver_id == current_user.id:
        req.status = 'rejected'
        db.session.commit()
        flash("Request rejected!", "info")
    return redirect(url_for('profile'))

@app.route('/swap_request/update/<int:request_id>')
@login_required
def update_swap_request(request_id):
    action = request.args.get('action')
    req = SkillSwapRequest.query.get_or_404(request_id)

    if req.receiver_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for('profile'))

    if action == 'accept':
        req.status = 'accepted'
    elif action == 'reject':
        req.status = 'rejected'
    elif action == 'confirm':
        req.status = 'confirmed'
    else:
        flash("Invalid action.", "danger")
        return redirect(url_for('profile'))

    db.session.commit()
    flash(f"Swap request {action}ed.", "success")
    return redirect(url_for('profile'))

@app.route("/recommend_skills/<int:user_id>")
@login_required
def recommend_skills(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    all_users = User.query.filter(User.id != user.id).all()
    all_skills = [u.skills_offered or "" for u in all_users]
    current_skills = user.skills_offered or ""
    all_skills.append(current_skills)

    vectorizer = CountVectorizer().fit_transform(all_skills)
    similarity = cosine_similarity(vectorizer)

    scores = list(enumerate(similarity[-1][:-1]))
    scores.sort(key=lambda x: x[1], reverse=True)

    recommendations = []
    for idx, score in scores:
        other_user = all_users[idx]
        if score > 0.2:
            for skill in other_user.skills_offered.split(","):
                skill = skill.strip()
                if skill and skill not in current_skills:
                    recommendations.append(skill)

    unique_recommendations = list(set(recommendations))[:5]
    return jsonify({"recommendations": unique_recommendations})

@app.route('/generate_skill_path', methods=['POST'])
@login_required
def generate_skill_path():
    desired_skill = request.form.get('desired_skill', '').strip().lower()
    skill_paths = {
        "web development": ["HTML", "CSS", "JavaScript", "Flask", "React"],
        "data science": ["Python", "Pandas", "Matplotlib", "Scikit-learn", "Deep Learning"],
        "machine learning": ["Python", "Numpy", "Scikit-learn", "TensorFlow"],
        "android development": ["Java", "XML", "Android Studio", "Firebase"]
    }
    recommendations = skill_paths.get(desired_skill, [])
    other_users = User.query.filter(User.id != current_user.id).all()
    incoming_requests = SkillSwapRequest.query.filter_by(receiver_id=current_user.id).all()
    outgoing_requests = SkillSwapRequest.query.filter_by(sender_id=current_user.id).all()
    return render_template('profile.html', user=current_user, other_users=other_users,
                           incoming_requests=incoming_requests, outgoing_requests=outgoing_requests,
                           skill_path=recommendations)

@app.route('/location_based_users')
@login_required
def location_based_users():
    if not current_user.location:
        flash("Please update your location in profile to see nearby users.")
        return redirect(url_for('profile'))
    users = User.query.filter_by(location=current_user.location).filter(User.id != current_user.id).all()
    return render_template('location_users.html', users=users, current_location=current_user.location)

# ----------------- Run App -----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5050)
