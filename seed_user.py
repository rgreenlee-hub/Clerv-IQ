# seed_user.py
from app import db, User, bcrypt, app

with app.app_context():
    # Check if user already exists
    if not User.query.filter_by(email="admin@example.com").first():
        user = User(
            email="admin@example.com",
            password=bcrypt.generate_password_hash("password123").decode("utf-8"),
            onboarding_complete=True,
            client_id=1
        )
        db.session.add(user)
        db.session.commit()
        print("✅ Admin user created: admin@example.com / password123")
    else:
        print("⚠️ User already exists")
