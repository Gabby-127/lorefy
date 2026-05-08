from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from flask_bcrypt import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    characters = db.relationship("Character", backref="owner", lazy=True, cascade="all, delete-orphan")
    chat_sessions = db.relationship("ChatSession", backref="user", lazy=True, cascade="all, delete-orphan")
    relationships = db.relationship("Relationship", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer)
    birthday = db.Column(db.String(10))  # YYYY-MM-DD format
    zodiac = db.Column(db.String(20))
    height = db.Column(db.String(50))
    homeland = db.Column(db.String(120))
    background = db.Column(db.Text, nullable=False)
    personality = db.Column(db.Text, nullable=False)
    mbti = db.Column(db.String(4))
    temperament = db.Column(db.String(20))  # Sanguine, Choleric, Melancholic, Phlegmatic
    quote = db.Column(db.String(255))
    misc = db.Column(db.Text)
    profile_image_path = db.Column(db.String(255))  # Album cover / profile picture
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assets = db.relationship("CharacterAsset", backref="character", lazy=True, cascade="all, delete-orphan")


class CharacterAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey("character.id"), nullable=False)
    emotion = db.Column(db.String(20), nullable=False)  # neutral, happy, frustrated, sad, smug
    file_path = db.Column(db.String(255), nullable=False)


class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    character_a_id = db.Column(db.Integer, db.ForeignKey("character.id"), nullable=False)
    character_b_id = db.Column(db.Integer, db.ForeignKey("character.id"), nullable=False)
    scenario = db.Column(db.String(255), nullable=False)
    turn_count = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    character_a = db.relationship("Character", foreign_keys=[character_a_id])
    character_b = db.relationship("Character", foreign_keys=[character_b_id])
    messages = db.relationship("ChatMessage", backref="session", lazy=True, cascade="all, delete-orphan")


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id"), nullable=False)
    speaker = db.Column(db.String(1), nullable=False)  # "A" or "B"
    content = db.Column(db.Text, nullable=False)
    emotion = db.Column(db.String(20), default="neutral")
    turn_number = db.Column(db.Integer, nullable=False)


class Relationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    character_a_id = db.Column(db.Integer, db.ForeignKey("character.id"), nullable=False)
    character_b_id = db.Column(db.Integer, db.ForeignKey("character.id"), nullable=False)
    score = db.Column(db.Integer, default=5)  # 1-10 scale
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    character_a = db.relationship("Character", foreign_keys=[character_a_id])
    character_b = db.relationship("Character", foreign_keys=[character_b_id])

    def get_label(self):
        labels = {
            1: "Enemies",
            2: "Rivals",
            3: "Dislike",
            4: "Wary",
            5: "Indifferent",
            6: "Acquaintances",
            7: "Friendly",
            8: "Friends",
            9: "Close",
            10: "Inseparable"
        }
        return labels.get(self.score, "Indifferent")
