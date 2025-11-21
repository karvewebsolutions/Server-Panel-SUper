
import os
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth import get_password_hash

def create_admin(db: Session, email: str, password: str):
    admin = db.query(User).filter(User.email == email).first()
    if not admin:
        admin = User(
            email=email,
            hashed_password=get_password_hash(password),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin user {email} created successfully.")
    else:
        print(f"Admin user {email} already exists.")

if __name__ == "__main__":
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required.")
        exit(1)

    with next(get_db()) as db:
        create_admin(db, email, password)
