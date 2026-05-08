# Lorefy

A creative character wiki and AI roleplay platform with a Spotify-inspired dark UI. Create character profiles, manage emotion assets, and watch your characters interact autonomously through AI-powered conversations.

## Features

- **Character Creation**: Build detailed character profiles with background, personality, MBTI, temperament, and emotion assets
- **Character Wiki**: Spotify-style wiki pages showcasing your characters with dark theme design
- **AI Roleplay**: Watch two characters chat autonomously for 12 turns driven by their personalities and lore
- **Relationship System**: Track character relationships on a 1-10 scale (Enemies → Inseparable)
- **Interactive Interventions**: Make decisions at dramatic moments to influence the conversation
- **Emotion Assets**: Upload up to 5 emotion sprites (neutral, happy, frustrated, sad, smug) per character

## Tech Stack

- **Backend**: Python 3, Flask, Flask-Login, Flask-SQLAlchemy, SQLite
- **AI**: Groq Python SDK with Llama 3.3 70B model
- **Frontend**: Jinja2 templates, vanilla CSS, vanilla JavaScript
- **Auth**: bcrypt for password hashing
- **Environment**: python-dotenv for configuration

## Setup Instructions

### 1. Create Virtual Environment

On Windows (PowerShell or CMD):
```bash
python -m venv venv
venv\Scripts\activate
```

On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your actual values:
```
SECRET_KEY=your-secret-key-here-change-this
GROQ_API_KEY=your-groq-api-key-here
```

To get a Groq API key, visit: https://console.groq.com

### 4. Run the Application

```bash
python app.py
```

The app will start at `http://localhost:5000`

- SQLite database (`lorefy.db`) is created automatically
- All tables are initialized on first run

### 5. First Steps

1. Sign up with a username, email, and password
2. Create your first character with background and personality
3. Upload emotion assets (or skip for now)
4. View your character's wiki page
5. Create another character
6. Go to "Start Chat" and pick a scenario
7. Watch them chat!

## Project Structure

```
lorefy/
├── app.py                      # Main Flask application and routes
├── models.py                   # Database models
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script (macOS/Linux)
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── static/
│   ├── css/
│   │   └── style.css          # Global styles (single file)
│   ├── js/
│   │   └── chat.js            # Chat UI JavaScript
│   └── uploads/               # User-uploaded character assets (git-ignored)
└── templates/
    ├── base.html              # Base template
    ├── index.html             # Home / character roster
    ├── login.html             # Login page
    ├── signup.html            # Signup page
    ├── character_new.html     # Create character form
    ├── character_edit.html    # Edit character form
    ├── character_wiki.html    # Character wiki page
    ├── chat_setup.html        # Chat scenario selection
    └── chat.html              # Active chat page
```

## Database Models

### User
- `id`, `username`, `email`, `password_hash`, `created_at`

### Character
- `id`, `user_id` (FK), `name`, `age`, `birthday`, `zodiac`, `height`, `homeland`, `background`, `personality`, `mbti`, `temperament`, `quote`, `misc`, `created_at`

### CharacterAsset
- `id`, `character_id` (FK), `emotion` (neutral/happy/frustrated/sad/smug), `file_path`

### ChatSession
- `id`, `user_id` (FK), `character_a_id` (FK), `character_b_id` (FK), `scenario`, `turn_count`, `is_complete`, `created_at`

### ChatMessage
- `id`, `session_id` (FK), `speaker` (A/B), `content`, `emotion`, `turn_number`

### Relationship
- `id`, `user_id` (FK), `character_a_id` (FK), `character_b_id` (FK), `score` (1-10), `updated_at`

## Security Features

- Passwords hashed with bcrypt
- Parameterized database queries via SQLAlchemy ORM
- File upload validation (type, size, filename)
- Ownership checks on all character/asset routes
- Environment variables for secrets (never committed)
- CSRF protection via Flask-WTF

## Styling

All styles are centralized in `static/css/style.css`:
- CSS variables for Spotify-inspired dark theme
- Single source of truth (no inline styles, no style blocks)
- Responsive design for mobile/tablet/desktop
- Smooth transitions and hover effects

## Chat AI System

The chat endpoint uses Groq's Llama 3.3 70B model to:

1. Generate two lines of dialogue (one per character) in natural conversation
2. Return JSON metadata with:
   - Emotion for each character (neutral/happy/frustrated/sad/smug)
   - Relationship delta (-2 to +2)
   - Optional intervention trigger for dramatic moments

The AI respects character lore, personality, MBTI, temperament, and conversation history.

## Relationship Scoring

| Score | Label |
|-------|-------|
| 1 | Enemies |
| 2 | Rivals |
| 3 | Dislike |
| 4 | Wary |
| 5 | Indifferent |
| 6 | Acquaintances |
| 7 | Friendly |
| 8 | Friends |
| 9 | Close |
| 10 | Inseparable |

## Troubleshooting

### Port already in use
Flask defaults to port 5000. If it's in use, modify the last line of `app.py`:
```python
app.run(debug=True, port=5001)  # Change to another port
```

### Database corruption
Delete `lorefy.db` and restart the app to recreate it.

### Groq API errors
- Verify your `GROQ_API_KEY` is valid
- Check Groq console for rate limits or quota issues
- Ensure you have access to the `llama-3.3-70b-versatile` model

### File uploads not appearing
- Check `static/uploads/` folder permissions
- Ensure uploaded file is PNG or JPG and under 2MB
- Verify user folder structure: `static/uploads/<user_id>/<character_id>/`

## Development Tips

- Use Firefox DevTools to inspect the dark theme colors
- Test chat with characters that have contrasting personalities
- Create relationships by running multiple chats between the same characters
- Try different scenarios to see how they influence dialogue

## License

This project is provided as-is for personal and educational use.

## Support

For issues or feature requests, check the code or review the specification document.