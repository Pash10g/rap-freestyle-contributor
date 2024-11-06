# Rap Freestyle Word Contributor Client

This is a client application for the Rap Freestyle Word Generator. Unlike the admin app, this version allows users to:

- View the current round's prompt
- Add words to the current round
- Vote on existing words
- View previous rounds and their generated songs

## Key Differences from Admin App

- Cannot start new rounds
- Cannot generate songs
- Focused on word contribution and voting

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your MongoDB URI:
```
MONGODB_URI=your_mongodb_connection_string
```

3. Run the app:
```bash
streamlit run app.py
```

## Usage

- Add words that you think would make an interesting rap song
- Vote for words you like
- Explore previous rounds and their generated songs

## Workflow

1. When the app starts, it connects to the MongoDB database
2. You'll see the current round's prompt and remaining character limit
3. Add words that contribute to the rap song's theme
4. Vote for words you find most interesting
5. View previous rounds to see how songs were generated based on community-contributed words
