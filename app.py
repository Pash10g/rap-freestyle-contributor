import streamlit as st
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, UTC
from bson import ObjectId

# Load environment variables
load_dotenv()

# Constants
BASE_PROMPT = "Create a cool rap song with the following words that must be in it: "
CHAR_LIMIT = 200

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['suno_rap']
words_collection = db['rap_words']
rounds_collection = db['generation_rounds']

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(ObjectId())

def add_word(word, current_round):
    """Add a new word to the database"""
    current_words = list(words_collection.find({
        'round_id': current_round['_id']
    }))
    
    new_words = current_words + [{'word': word}]
    new_total_length = calculate_prompt_length(new_words)
    
    if new_total_length > CHAR_LIMIT:
        return False, "Adding this word would exceed the character limit"
    
    word_doc = {
        'word': word,
        'votes': [],
        'created_at': datetime.now(UTC),
        'created_by': st.session_state.user_id,
        'round_id': current_round['_id']
    }
    words_collection.insert_one(word_doc)
    
    rounds_collection.update_one(
        {'_id': current_round['_id']},
        {'$set': {'total_chars': new_total_length}}
    )
    return True, "Word added successfully"

def vote_for_song(round_id):
    """Add user vote for a song in a completed round"""
    round = rounds_collection.find_one({'_id': round_id})
    if not round or 'generated_songs' not in round:
        return False
    
    # Initialize votes array if it doesn't exist
    if 'votes' not in round:
        rounds_collection.update_one(
            {'_id': round_id},
            {'$set': {'votes': []}}
        )
        round['votes'] = []
    
    # Check if user already voted in this round
    if st.session_state.user_id not in [vote['user_id'] for vote in round.get('votes', [])]:
        vote = {
            'user_id': st.session_state.user_id,
            'timestamp': datetime.now(UTC)
        }
        rounds_collection.update_one(
            {'_id': round_id},
            {'$push': {'votes': vote}}
        )
        return True
    return False

def vote_for_word(word_id):
    """Add user vote for a word"""
    word = words_collection.find_one({'_id': word_id})
    if st.session_state.user_id not in [vote['user_id'] for vote in word.get('votes', [])]:
        vote = {
            'user_id': st.session_state.user_id,
            'timestamp': datetime.now(UTC)
        }
        words_collection.update_one(
            {'_id': word_id},
            {'$push': {'votes': vote}}
        )

def calculate_prompt_length(words):
    """Calculate total prompt length including base prompt and spaces"""
    if not words:
        return len(BASE_PROMPT)
    
    words_text = " ".join(word['word'] for word in words)
    full_prompt = f"{BASE_PROMPT}{words_text}"
    return len(full_prompt)

def get_current_round_words(current_round):
    """Get all words for current round sorted by vote count"""
    return list(words_collection.find({
        'round_id': current_round['_id']
    }).sort([('votes', -1)]))

def get_current_round():
    """Get the current active round"""
    current_round = rounds_collection.find_one({'status': 'active'})
    
    # If no active round exists, create one
    if not current_round:
        current_round = {
            'round_number': rounds_collection.count_documents({}) + 1,
            'status': 'active',
            'created_at': datetime.now(UTC),
            'total_chars': len(BASE_PROMPT)
        }
        rounds_collection.insert_one(current_round)
    
    return current_round

def get_previous_rounds():
    """Get previous rounds sorted by votes"""
    previous_rounds = list(rounds_collection.find({'status': 'completed'}))
    
    # Add vote count to each round
    for round in previous_rounds:
        round['vote_count'] = len(round.get('votes', []))
    
    # Sort by votes (descending) and then by round number (descending)
    previous_rounds.sort(key=lambda x: (-x['vote_count'], -x['round_number']))
    return previous_rounds

def get_current_prompt(current_round):
    """Get the current prompt with all words"""
    words = get_current_round_words(current_round)
    if not words:
        return BASE_PROMPT
    
    words_text = " ".join(word['word'] for word in words)
    return f"{BASE_PROMPT}{words_text}"

# Streamlit UI
st.title('🎵 Rap Freestyle Word Contributor')

# Get current round
current_round = get_current_round()

# Display current prompt and character count
current_prompt = get_current_prompt(current_round)
total_chars = len(current_prompt)
chars_remaining = CHAR_LIMIT - total_chars

st.text_area("Current Prompt", current_prompt, height=100, disabled=True)
col1, col2 = st.columns(2)
with col1:
    st.metric('Total Characters', total_chars)
with col2:
    st.metric('Characters Remaining', chars_remaining)
st.progress(total_chars / CHAR_LIMIT)

# Word input section
if chars_remaining > 0:
    st.subheader('Add New Word')
    with st.form('add_word_form'):
        new_word = st.text_input('Enter a word:')
        submitted = st.form_submit_button('Add Word')
        
        if submitted and new_word:
            success, message = add_word(new_word, current_round)
            if success:
                st.success(f'Added: {new_word}')
                st.rerun()
            else:
                st.error(message)

# Display existing words
st.subheader('Current Round Words')
words = get_current_round_words(current_round)

for word in words:
    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    with col1:
        st.write(word['word'])
    with col2:
        vote_count = len(word.get('votes', []))
        st.write(f"Votes: {vote_count}")
    with col3:
        user_voted = st.session_state.user_id in [vote['user_id'] for vote in word.get('votes', [])]
        if user_voted:
            st.write('✅ Voted')
        else:
            if st.button('👍 Vote', key=str(word['_id'])):
                vote_for_word(word['_id'])
                st.rerun()
    with col4:
        if word.get('created_by') == st.session_state.user_id:
            st.write('(Your word)')

# Display previous rounds
st.markdown('---')
st.subheader('Previous Rounds')
previous_rounds = get_previous_rounds()
for round in previous_rounds:
    user_voted = st.session_state.user_id in [vote['user_id'] for vote in round.get('votes', [])]
    with st.expander(f"Round #{round['round_number']} - {round['vote_count']} votes"):
        round_words = words_collection.find({'round_id': round['_id']}).sort([('votes', -1)])
        words_list = list(round_words)
        if words_list:
            words_text = " ".join(word['word'] for word in words_list)
            full_prompt = f"{BASE_PROMPT}{words_text}"
            st.text_area("Final Prompt", full_prompt, height=100, disabled=True)
            
            # Display words used
            st.markdown("### Words Used")
            for word in words_list:
                st.write(f"{word['word']} - {len(word.get('votes', []))} votes")
            
            # Display generated songs if available
            if 'generated_songs' in round:
                songs = round['generated_songs']
                
                # Display Song 1
                st.markdown('### Song 1')
                if songs[0].get('lyric'):
                    st.markdown("#### Lyrics")
                    st.markdown(songs[0]['lyric'].replace('\n', '<br>'), unsafe_allow_html=True)
                
                if songs[0].get('audio_url'):
                    st.audio(songs[0]['audio_url'])
                
                # Display Song 2
                st.markdown('### Song 2')
                if songs[1].get('lyric'):
                    st.markdown("#### Lyrics")
                    st.markdown(songs[1]['lyric'].replace('\n', '<br>'), unsafe_allow_html=True)
                
                if songs[1].get('audio_url'):
                    st.audio(songs[1]['audio_url'])

                # Show vote button if user hasn't voted
                if not user_voted:
                    if st.button('👍 Vote for this round', key=f"vote_{round['_id']}"):
                        if vote_for_song(round['_id']):
                            st.rerun()
                else:
                    st.write('✅ You voted for this round')
        else:
            st.write("No words were added in this round")
