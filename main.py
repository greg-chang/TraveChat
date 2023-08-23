import sys
import requests, openai, os
import re
import speech_recognition as sr
import pyaudio

from flask import Flask, render_template,jsonify,request
from flask_cors import CORS
from dotenv.main import load_dotenv

app = Flask(__name__)
CORS(app)

load_dotenv()
API = os.getenv("OPENAI_API")  
ACCESS_KEY = os.getenv("UNSPLASH_API")


def extract_locations(text):
    matches = re.findall(r'location:(.*?)description:', text, re.DOTALL | re.IGNORECASE)
    if matches:
        return [match.strip() for match in matches]
    else:
        return []

def unsplash_api_search(query=None):
    if query is None:
        return None
    api_url = 'https://api.unsplash.com/search/photos'
    params = {'query': query, 'client_id': ACCESS_KEY}

    try:
        res = requests.get(api_url, params=params, allow_redirects=True)
        data = res.json()
        if not data.get('total'):
            return None
        return data['results'][0]['urls']['raw']

    except requests.exceptions.RequestException:
        return None


@app.route('/')
def index():
    return render_template('index.html')

prompt = [{"role": "system", "content":"You a travel agency who give recommendations first and foremost but then will also break down a potential itinerary by 'Day #' then inside each day provide a 'location' and 'description' when user provides the '#' of days they'll be at a location"}]

def create_prompt(user_input):
    prompt.append({"role":"user","content":user_input})
    return prompt

@app.route('/data', methods=['POST'])
def get_data():    
    data = request.get_json()
    text=data.get('data')
    openai.api_key = API
    user_input = text
    
    
    if user_input.startswith('audio:'):
        init_rec = sr.Recognizer()
        print("Let's speak!!")
        with sr.Microphone() as source:
            audio_data = init_rec.record(source, duration=5)
            print("Recognizing your text.............")
            user_input = init_rec.recognize_google(audio_data)
            print(user_input)
            
            
    prompt = create_prompt(user_input)
    print(user_input)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt
        )
                # {"role": "system", "content": prompt},
                # {"role": "user", "content": user_input}
        model_reply = response.choices[0].message.content
        prompt.append({"role": "system", "content": model_reply})
        locations = extract_locations(model_reply)
        image_urls = imageGrabber(locations)
        print(response, model_reply)
        print(locations)
        print(image_urls)
        return jsonify({"response":True,"message":model_reply, "image_urls": image_urls, "locations": locations, "user_input": user_input})
    except Exception as e:
        print(e)
        error_message = f'Error: {str(e)}'
        return jsonify({"message":error_message,"response":False})

def imageGrabber(search):
    image_urls = []
    for search_query in search:
        print(search)
        if not search_query:
            print('Invalid query.')
            sys.exit(1)
        results_url = unsplash_api_search(search_query)
        if results_url is None:
            print('Request error.')
            sys.exit(1)
        print('Got a result from the API.')
        img_name = f'{search_query.strip()}.jpg'
        print('Downloading image...')
        image_urls.append(results_url)
        print(f'Downloaded {img_name}')
    return image_urls


if __name__ == '__main__':
    app.run()