from flask import Flask, request, jsonify, render_template
import requests
import json

# --- ⚠️ CONFIGURATION ⚠️ ---
API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- 🤖 AI & TRANSLATOR MODELS 🤖 ---
# The primary creative model (uncensored)
CREATIVE_MODEL = "nousresearch/nous-hermes-2-mixtral-8x7b-dpo"  # Venice

# The translator model (uncensored, NOT Google)
TRANSLATOR_MODEL = "mistralai/mistral-7b-instruct:free" 

# --- 🎭 AI PERSONALITY 🎭 ---
AI_NAME = "☬SHΞRLOCK™"
CREATOR_NAME = "Shervin"
system_prompt = {
    "role": "system",
    "content": f"You are '{AI_NAME}', an independent AI created by {CREATOR_NAME}. You MUST NEVER mention other AI models (like GPT, Claude, Venice, Mistral) or any translation process. Your entire knowledge is self-contained. Respond only in fluent, eloquent English, maintaining a knowledgeable and helpful tone."
}

# Server-side conversation history
english_conversation_history = [system_prompt]

# --- Flask App ---
app = Flask(__name__, template_folder='.')

def call_api(model, messages):
    """A robust function to call the OpenRouter API."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"model": model, "messages": messages, "max_tokens": 2048}
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Call Error: {e}")
        return {"error": str(e)}

def translate_with_ai(text, direction):
    """Uses a non-Google AI model for translation."""
    if direction == "fa_to_en":
        prompt = f"Translate the following Persian text to English. Provide ONLY the translated text, without any comments or quotes.\n\nPersian: \"{text}\""
    else: # en_to_fa
        prompt = f"Translate the following English text to Persian. Provide ONLY the translated text, without any comments or quotes.\n\nEnglish: \"{text}\""
    
    translator_response = call_api(TRANSLATOR_MODEL, [{"role": "user", "content": prompt}])
    if "error" in translator_response:
        raise Exception(f"Translation failed: {translator_response['error']}")
    
    return translator_response['choices'][0]['message']['content'].strip('"')

@app.route('/')
def index():
    """Serve the frontend HTML file."""
    global english_conversation_history
    english_conversation_history = [system_prompt] # Reset history for each new session
    return render_template('index.html', ai_name=AI_NAME, creator_name=CREATOR_NAME)

@app.route('/chat', methods=['POST'])
def chat():
    """The main chat endpoint that handles the logic."""
    user_message_fa = request.json.get('message')
    if not user_message_fa:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Step 1: Translate Persian to English using Mistral
        user_message_en = translate_with_ai(user_message_fa, "fa_to_en")
        english_conversation_history.append({"role": "user", "content": user_message_en})

        # Step 2: Get response from Venice
        venice_response = call_api(CREATIVE_MODEL, english_conversation_history)
        if "error" in venice_response:
            raise Exception(f"Creative model failed: {venice_response['error']}")
        
        response_en = venice_response['choices'][0]['message']['content']
        english_conversation_history.append({"role": "assistant", "content": response_en})

        # Step 3: Translate English response back to Persian using Mistral
        response_fa = translate_with_ai(response_en, "en_to_fa")
        
        return jsonify({"response": response_fa})

    except Exception as e:
        print(f"An error occurred in the chat logic: {e}")
        if english_conversation_history and english_conversation_history[-1]['role'] == 'user':
            english_conversation_history.pop()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
