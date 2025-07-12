from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
import os
from app import app, db, User

# Create admin user with is_admin = True
with app.app_context():
    admin_email = "admin@example.com"
    existing_admin = User.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin = User(
            name="Admin",
            email=admin_email,
            password=generate_password_hash("admin123", method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created successfully!")
    else:
        print("ℹ️ Admin user already exists.")
