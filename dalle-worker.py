import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# --- Configuration ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL_IMAGE = "https://api.openai.com/v1/images/generations"
OPENAI_API_URL_CHAT = "https://api.openai.com/v1/chat/completions"
LISTEN_PORT = int(os.environ.get("PORT", 8082))

# Check API key
if not OPENAI_API_KEY:
    print("FATAL ERROR: Environment variable OPENAI_API_KEY belum di-set.")
    exit(1)

# --- Helper: Enhance Prompt using GPT ---
def enhance_prompt(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that rewrites image prompts to be more detailed and visually descriptive for DALL·E 3."
        },
        {
            "role": "user",
            "content": f"Rewrite this prompt to be more detailed and vivid for image generation: '{prompt}'"
        }
    ]

    payload = {
        "model": "gpt-4-turbo",  # Pastikan Anda punya akses ke model ini
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300
    }

    response = requests.post(OPENAI_API_URL_CHAT, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    return data["choices"][0]["message"]["content"].strip()

# --- Helper: Generate Image from Prompt ---
def generate_image_by_prompt(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }

    response = requests.post(OPENAI_API_URL_IMAGE, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    image_url = data.get("data", [{}])[0].get("url")
    if not image_url:
        raise ValueError("Gagal mengekstrak URL gambar dari response OpenAI")

    return image_url

# --- Route: Generate Image ---
@app.route('/generate-image', methods=['POST'])
def handle_generate_image():
    if not request.is_json:
        return jsonify({"error": "Request body harus berupa JSON"}), 400

    data = request.get_json()
    raw_prompt = data.get("prompt")

    if not raw_prompt:
        return jsonify({"error": "Field 'prompt' tidak ditemukan dalam JSON body"}), 400

    print(f"Menerima request untuk prompt: '{raw_prompt}'")

    try:
        enhanced_prompt = enhance_prompt(raw_prompt)
        print(f"Enhanced prompt: {enhanced_prompt}")
    except Exception as e:
        print(f"Gagal enhance prompt: {e}")
        return jsonify({"error": "Gagal enhance prompt", "details": str(e)}), 500

    try:
        image_url = generate_image_by_prompt(enhanced_prompt)
        print("Berhasil generate gambar.")
        return jsonify({"image_url": image_url})
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error dari OpenAI: {http_err}")
        try:
            error_details = http_err.response.json()
        except Exception:
            error_details = http_err.response.text
        return jsonify({
            "error": "Request ke OpenAI API gagal",
            "status_code": http_err.response.status_code,
            "details": error_details
        }), http_err.response.status_code
    except requests.exceptions.RequestException as req_err:
        print(f"Error koneksi saat memanggil OpenAI: {req_err}")
        return jsonify({"error": "Gagal menghubungi OpenAI API"}), 504
    except Exception as e:
        print(f"Terjadi error tidak terduga: {e}")
        return jsonify({"error": "Internal server error"}), 500

# --- Route: Health Check ---
@app.route('/')
def index():
    return "Python OpenAI Proxy Server is running!"

# --- Run Server ---
if __name__ == '__main__':
    print(f"Menjalankan OpenAI Proxy server di http://0.0.0.0:{LISTEN_PORT}")
    print("Pastikan environment variable OPENAI_API_KEY sudah di-set!")
    app.run(host='127.0.0.1', port=LISTEN_PORT, debug=False)