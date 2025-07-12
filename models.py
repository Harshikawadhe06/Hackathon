from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import app
from datetime import datetime
from app import db

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # New fields
    skills_offered = db.Column(db.String(200))
    skills_wanted = db.Column(db.String(200))
    availability = db.Column(db.String(100))
    location = db.Column(db.String(100))
    is_public = db.Column(db.Boolean, default=True)
    profile_photo = db.Column(db.String(300))  # Store file path or URL
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)

class SkillSwapRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, confirmed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')