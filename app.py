import os
import json
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from groq import Groq
from models import db, User, Character, CharacterAsset, ChatSession, ChatMessage, Relationship

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lorefy.db"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max request size

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
EMOTIONS = ["neutral", "happy", "frustrated", "sad", "smug"]
TEMPERAMENTS = ["Sanguine", "Choleric", "Melancholic", "Phlegmatic"]
MBTI_TYPES = [
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ"
]
SCENARIOS = [
    "Stuck in an elevator together",
    "Competing for the same goal",
    "Meeting for the first time at a party",
    "Forced to work together on a project",
    "One character needs a favour from the other",
    "A heated argument that escalated from nothing",
    "Sharing a meal at a restaurant",
    "Trapped somewhere dangerous together"
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_zodiac(birthday_str):
    """Calculate zodiac sign from birthday (YYYY-MM-DD format)"""
    if not birthday_str:
        return None
    try:
        month, day = map(int, birthday_str.split("-")[1:])
    except (ValueError, IndexError):
        return None
    
    zodiac_signs = [
        ("Capricorn", (12, 22), (1, 19)),
        ("Aquarius", (1, 20), (2, 18)),
        ("Pisces", (2, 19), (3, 20)),
        ("Aries", (3, 21), (4, 19)),
        ("Taurus", (4, 20), (5, 20)),
        ("Gemini", (5, 21), (6, 20)),
        ("Cancer", (6, 21), (7, 22)),
        ("Leo", (7, 23), (8, 22)),
        ("Virgo", (8, 23), (9, 22)),
        ("Libra", (9, 23), (10, 22)),
        ("Scorpio", (10, 23), (11, 21)),
        ("Sagittarius", (11, 22), (12, 21))
    ]
    
    for sign, (start_month, start_day), (end_month, end_day) in zodiac_signs:
        if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
            return sign
    return None


def character_owner_required(f):
    @wraps(f)
    def decorated_function(character_id, *args, **kwargs):
        character = Character.query.get_or_404(character_id)
        if character.user_id != current_user.id:
            return {"error": "Forbidden"}, 403
        return f(character_id, *args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    characters = Character.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", characters=characters)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not username or not email or not password:
            return render_template("signup.html", error="All fields required")
        
        if User.query.filter_by(username=username).first():
            return render_template("signup.html", error="Username already exists")
        
        if User.query.filter_by(email=email).first():
            return render_template("signup.html", error="Email already exists")
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for("index"))
    
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        
        return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/character/new", methods=["GET", "POST"])
@login_required
def character_new():
    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        birthday = request.form.get("birthday")
        height = request.form.get("height")
        homeland = request.form.get("homeland")
        background = request.form.get("background")
        personality = request.form.get("personality")
        mbti = request.form.get("mbti")
        temperament = request.form.get("temperament")
        quote = request.form.get("quote")
        misc = request.form.get("misc")
        
        if not name or not background or not personality:
            return render_template("character_new.html", error="Name, background, and personality are required")
        
        zodiac = get_zodiac(birthday) if birthday else None
        
        character = Character(
            user_id=current_user.id,
            name=name,
            age=int(age) if age else None,
            birthday=birthday,
            zodiac=zodiac,
            height=height,
            homeland=homeland,
            background=background,
            personality=personality,
            mbti=mbti,
            temperament=temperament,
            quote=quote,
            misc=misc
        )
        db.session.add(character)
        db.session.flush()
        
        # Create upload directory
        upload_dir = f"static/uploads/{current_user.id}/{character.id}"
        os.makedirs(upload_dir, exist_ok=True)

        # Handle profile image upload
        profile_file = request.files.get("profile_image")
        if profile_file and profile_file.filename and allowed_file(profile_file.filename):
            ext = profile_file.filename.rsplit(".", 1)[1].lower()
            profile_filename = f"profile.{ext}"
            profile_filepath = os.path.join(upload_dir, profile_filename)
            profile_file.save(profile_filepath)
            character.profile_image_path = f"{upload_dir}/{profile_filename}"

        # Handle file uploads
        for emotion in EMOTIONS:
            file_key = f"emotion_{emotion}"
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename and allowed_file(file.filename):
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    filename = f"{emotion}.{ext}"
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    
                    asset = CharacterAsset(
                        character_id=character.id,
                        emotion=emotion,
                        file_path=f"{upload_dir}/{filename}"
                    )
                    db.session.add(asset)
        
        db.session.commit()
        return redirect(url_for("character_wiki", character_id=character.id))
    
    return render_template("character_new.html", mbti_types=MBTI_TYPES, temperaments=TEMPERAMENTS)


@app.route("/character/<int:character_id>")
@login_required
def character_wiki(character_id):
    character = Character.query.get_or_404(character_id)
    if character.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    relationships = Relationship.query.filter(
        ((Relationship.character_a_id == character_id) | (Relationship.character_b_id == character_id)),
        Relationship.user_id == current_user.id
    ).all()
    
    assets_by_emotion = {asset.emotion: asset for asset in character.assets}
    
    return render_template(
        "character_wiki.html",
        character=character,
        assets_by_emotion=assets_by_emotion,
        relationships=relationships,
        emotions=EMOTIONS
    )


@app.route("/character/<int:character_id>/edit", methods=["GET", "POST"])
@login_required
def character_edit(character_id):
    character = Character.query.get_or_404(character_id)
    if character.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    if request.method == "POST":
        character.name = request.form.get("name", character.name)
        character.age = int(request.form.get("age")) if request.form.get("age") else None
        character.birthday = request.form.get("birthday", character.birthday)
        character.height = request.form.get("height", character.height)
        character.homeland = request.form.get("homeland", character.homeland)
        character.background = request.form.get("background", character.background)
        character.personality = request.form.get("personality", character.personality)
        character.mbti = request.form.get("mbti", character.mbti)
        character.temperament = request.form.get("temperament", character.temperament)
        character.quote = request.form.get("quote", character.quote)
        character.misc = request.form.get("misc", character.misc)
        
        if character.birthday:
            character.zodiac = get_zodiac(character.birthday)
        
        # Create upload directory
        upload_dir = f"static/uploads/{current_user.id}/{character.id}"
        os.makedirs(upload_dir, exist_ok=True)

        # Handle profile image upload
        profile_file = request.files.get("profile_image")
        if profile_file and profile_file.filename and allowed_file(profile_file.filename):
            if character.profile_image_path:
                try:
                    os.remove(character.profile_image_path)
                except OSError:
                    pass
            ext = profile_file.filename.rsplit(".", 1)[1].lower()
            profile_filename = f"profile.{ext}"
            profile_filepath = os.path.join(upload_dir, profile_filename)
            profile_file.save(profile_filepath)
            character.profile_image_path = f"{upload_dir}/{profile_filename}"

        # Handle file uploads
        for emotion in EMOTIONS:
            file_key = f"emotion_{emotion}"
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename and allowed_file(file.filename):
                    # Remove old file
                    old_asset = CharacterAsset.query.filter_by(
                        character_id=character.id,
                        emotion=emotion
                    ).first()
                    if old_asset:
                        try:
                            os.remove(old_asset.file_path)
                        except OSError:
                            pass
                        db.session.delete(old_asset)
                    
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    filename = f"{emotion}.{ext}"
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    
                    asset = CharacterAsset(
                        character_id=character.id,
                        emotion=emotion,
                        file_path=f"{upload_dir}/{filename}"
                    )
                    db.session.add(asset)
        
        db.session.commit()
        return redirect(url_for("character_wiki", character_id=character.id))
    
    assets_by_emotion = {asset.emotion: asset for asset in character.assets}
    return render_template(
        "character_edit.html",
        character=character,
        assets_by_emotion=assets_by_emotion,
        mbti_types=MBTI_TYPES,
        temperaments=TEMPERAMENTS,
        emotions=EMOTIONS
    )


@app.route("/chat/setup", methods=["GET", "POST"])
@login_required
def chat_setup():
    characters = Character.query.filter_by(user_id=current_user.id).all()
    
    if request.method == "POST":
        character_a_id = request.form.get("character_a_id")
        character_b_id = request.form.get("character_b_id")
        scenario = request.form.get("scenario")
        
        if not character_a_id or not character_b_id or not scenario:
            return render_template("chat_setup.html", characters=characters, scenarios=SCENARIOS, error="All fields required")
        
        char_a = Character.query.get(character_a_id)
        char_b = Character.query.get(character_b_id)
        
        if not char_a or not char_b or char_a.user_id != current_user.id or char_b.user_id != current_user.id:
            return render_template("chat_setup.html", characters=characters, scenarios=SCENARIOS, error="Invalid characters")
        
        if character_a_id == character_b_id:
            return render_template("chat_setup.html", characters=characters, scenarios=SCENARIOS, error="Cannot select the same character twice")
        
        chat_session = ChatSession(
            user_id=current_user.id,
            character_a_id=character_a_id,
            character_b_id=character_b_id,
            scenario=scenario
        )
        db.session.add(chat_session)
        db.session.commit()
        
        return redirect(url_for("chat", session_id=chat_session.id))
    
    return render_template("chat_setup.html", characters=characters, scenarios=SCENARIOS)


@app.route("/chat/<int:session_id>")
@login_required
def chat(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    if chat_session.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    relationship = Relationship.query.filter(
        ((Relationship.character_a_id == chat_session.character_a_id) & (Relationship.character_b_id == chat_session.character_b_id)) |
        ((Relationship.character_a_id == chat_session.character_b_id) & (Relationship.character_b_id == chat_session.character_a_id)),
        Relationship.user_id == current_user.id
    ).first()
    
    if not relationship:
        relationship = Relationship(
            user_id=current_user.id,
            character_a_id=chat_session.character_a_id,
            character_b_id=chat_session.character_b_id,
            score=5
        )
        db.session.add(relationship)
        db.session.commit()
    
    return render_template("chat.html", chat_session=chat_session, relationship=relationship)


def get_character_profile(character):
    """Get character profile as a string for AI context"""
    profile = f"Name: {character.name}\n"
    if character.age:
        profile += f"Age: {character.age}\n"
    if character.zodiac:
        profile += f"Zodiac: {character.zodiac}\n"
    if character.mbti:
        profile += f"MBTI: {character.mbti}\n"
    if character.temperament:
        profile += f"Temperament: {character.temperament}\n"
    if character.quote:
        profile += f"Signature Quote: \"{character.quote}\"\n"
    if character.background:
        profile += f"Background: {character.background}\n"
    if character.personality:
        profile += f"Personality: {character.personality}\n"
    if character.misc:
        profile += f"Misc: {character.misc}\n"
    return profile


def parse_groq_response(response_text):
    """Parse Groq response to extract dialogue and JSON metadata"""
    try:
        # Find the outermost JSON object that contains speaker_a_emotion.
        # [^{}]* breaks when intervention is a nested object, so we use a
        # bracket-depth scanner instead.
        start = None
        for i, ch in enumerate(response_text):
            if ch == '{' and '"speaker_a_emotion"' in response_text[i:i+200]:
                start = i
                break

        if start is None:
            # Fallback: find any { and scan forward matching brackets
            for i, ch in enumerate(response_text):
                if ch == '{':
                    start = i
                    break

        if start is None:
            return None, None, None, "No JSON found"

        depth = 0
        end = None
        for i in range(start, len(response_text)):
            if response_text[i] == '{':
                depth += 1
            elif response_text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        if end is None:
            return None, None, None, "Unmatched braces"

        json_text = response_text[start:end]
        metadata = json.loads(json_text)

        # Validate we got the right object
        if "speaker_a_emotion" not in metadata:
            return None, None, None, "Wrong JSON object"

        # Extract dialogue lines (before JSON block)
        dialogue_section = response_text[:start].strip()
        lines = [line.strip() for line in dialogue_section.split("\n") if line.strip()]

        if len(lines) < 2:
            return None, None, None, "Not enough dialogue lines"

        message_a = lines[0]
        message_b = lines[1]

        return message_a, message_b, metadata, None
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        return None, None, None, str(e)


@app.route("/chat/<int:session_id>/turn", methods=["POST"])
@login_required
def chat_turn(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    if chat_session.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    if chat_session.is_complete or chat_session.turn_count >= 12:
        return {"error": "Chat is complete"}, 400
    
    data = request.get_json()
    player_choice = data.get("player_choice")
    
    char_a = chat_session.character_a
    char_b = chat_session.character_b
    
    relationship = Relationship.query.filter(
        ((Relationship.character_a_id == char_a.id) & (Relationship.character_b_id == char_b.id)) |
        ((Relationship.character_a_id == char_b.id) & (Relationship.character_b_id == char_a.id)),
        Relationship.user_id == current_user.id
    ).first()
    
    # Build conversation history
    history = ""
    for msg in chat_session.messages:
        speaker_name = char_a.name if msg.speaker == "A" else char_b.name
        history += f"{speaker_name}: {msg.content}\n"
    
    # Build system prompt
    system_prompt = f"""You are roleplaying two characters in a scene. Generate exactly two lines of dialogue, one from each character, naturally in character.

Scenario: {chat_session.scenario}

Character A Profile:
{get_character_profile(char_a)}

Character B Profile:
{get_character_profile(char_b)}

Current Relationship Score: {relationship.score}/10 ({relationship.get_label()})

Conversation so far:
{history}

{f'Player just chose: "{player_choice}"' if player_choice else ''}

Respond with:
1. First line - Character A's dialogue (start with "{char_a.name}:")
2. Second line - Character B's dialogue (start with "{char_b.name}:")
3. A JSON block in this exact format:
{{"speaker_a_emotion": "neutral", "speaker_b_emotion": "neutral", "relationship_delta": 0, "intervention": null}}

EMOTION RULES — read carefully:
- Available emotions: neutral, happy, frustrated, sad, smug
- You MUST pick the emotion that best matches what the character just said and felt in that line.
- Do NOT default to neutral unless the character is genuinely calm and expressionless.
- Use the full range. If a character is winning an argument → smug. If they're upset → frustrated or sad. If something good happens → happy.
- The two characters should frequently have DIFFERENT emotions from each other — one may be smug while the other is frustrated, etc.
- Emotions should CHANGE across turns as the scene develops. Avoid repeating the same emotion more than 2 turns in a row.

For relationship_delta use: -2 to +2
For intervention, use null or an object like:
{{"trigger": "brief trigger description", "option_1": "first option", "option_2": "second option"}}

Only include intervention for dramatic moments."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.8,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content
        message_a, message_b, metadata, error = parse_groq_response(response_text)
        
        if error or not message_a or not message_b or not metadata:
            metadata = {
                "speaker_a_emotion": "neutral",
                "speaker_b_emotion": "neutral",
                "relationship_delta": 0,
                "intervention": None
            }
            message_a = f"{char_a.name}: ..."
            message_b = f"{char_b.name}: ..."
        
        # Save messages
        msg_a = ChatMessage(
            session_id=session_id,
            speaker="A",
            content=message_a.replace(f"{char_a.name}: ", ""),
            emotion=metadata.get("speaker_a_emotion", "neutral"),
            turn_number=chat_session.turn_count + 1
        )
        msg_b = ChatMessage(
            session_id=session_id,
            speaker="B",
            content=message_b.replace(f"{char_b.name}: ", ""),
            emotion=metadata.get("speaker_b_emotion", "neutral"),
            turn_number=chat_session.turn_count + 1
        )
        db.session.add(msg_a)
        db.session.add(msg_b)
        
        # Update relationship
        delta = metadata.get("relationship_delta", 0)
        relationship.score = max(1, min(10, relationship.score + delta))
        
        # Update chat session
        chat_session.turn_count += 1
        if chat_session.turn_count >= 12:
            chat_session.is_complete = True
        
        db.session.commit()
        
        # Get asset paths
        asset_a = CharacterAsset.query.filter_by(
            character_id=char_a.id,
            emotion=metadata.get("speaker_a_emotion", "neutral")
        ).first()
        asset_b = CharacterAsset.query.filter_by(
            character_id=char_b.id,
            emotion=metadata.get("speaker_b_emotion", "neutral")
        ).first()
        
        asset_a_path = asset_a.file_path if asset_a else None
        asset_b_path = asset_b.file_path if asset_b else None
        
        return jsonify({
            "messages": [
                {
                    "speaker": "A",
                    "name": char_a.name,
                    "content": msg_a.content,
                    "emotion": metadata.get("speaker_a_emotion", "neutral")
                },
                {
                    "speaker": "B",
                    "name": char_b.name,
                    "content": msg_b.content,
                    "emotion": metadata.get("speaker_b_emotion", "neutral")
                }
            ],
            "speaker_a_emotion": metadata.get("speaker_a_emotion", "neutral"),
            "speaker_b_emotion": metadata.get("speaker_b_emotion", "neutral"),
            "speaker_a_asset": asset_a_path,
            "speaker_b_asset": asset_b_path,
            "relationship_score": relationship.score,
            "relationship_label": relationship.get_label(),
            "intervention": metadata.get("intervention"),
            "turn_count": chat_session.turn_count,
            "is_complete": chat_session.is_complete
        })
    
    except Exception as e:
        return {"error": f"Failed to generate response: {str(e)}"}, 500


@app.route("/chat/<int:session_id>/end", methods=["POST"])
@login_required
def chat_end(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    if chat_session.user_id != current_user.id:
        return {"error": "Forbidden"}, 403
    
    if chat_session.is_complete:
        return {"error": "Chat already complete"}, 400
    
    chat_session.is_complete = True
    db.session.commit()
    
    char_a = chat_session.character_a
    char_b = chat_session.character_b
    
    # Get conversation history
    history = ""
    for msg in chat_session.messages:
        speaker_name = char_a.name if msg.speaker == "A" else char_b.name
        history += f"{speaker_name}: {msg.content}\n"
    
    relationship = Relationship.query.filter(
        ((Relationship.character_a_id == char_a.id) & (Relationship.character_b_id == char_b.id)) |
        ((Relationship.character_a_id == char_b.id) & (Relationship.character_b_id == char_a.id)),
        Relationship.user_id == current_user.id
    ).first()
    
    # Generate summary
    summary_prompt = f"""Write a brief 2-3 sentence summary of this interaction between {char_a.name} and {char_b.name}.

Scenario: {chat_session.scenario}

Conversation:
{history}

Final relationship status: {relationship.get_label()} (score {relationship.score}/10)

Write only the summary, nothing else."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.7,
            max_tokens=150
        )
        summary = response.choices[0].message.content.strip()
    except:
        summary = "The interaction was memorable and will impact their relationship going forward."
    
    return jsonify({
        "summary": summary,
        "relationship_score": relationship.score,
        "relationship_label": relationship.get_label()
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)