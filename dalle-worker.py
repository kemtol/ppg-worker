import os
import requests # Untuk memanggil OpenAI API
from flask import Flask, request, jsonify # Framework web
from dotenv import load_dotenv # Untuk baca .env (opsional)

# Muat environment variables dari file .env (jika ada)
# Berguna saat development, tapi di production lebih baik set env var langsung
load_dotenv()

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- Konfigurasi ---
# Ambil API Key dari environment variable (CARA AMAN!)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/images/generations"
# Ganti port jika 5000 sudah dipakai
LISTEN_PORT = int(os.environ.get("PORT", 5000))
# -----------------

# Cek apakah API Key sudah diset saat startup
if not OPENAI_API_KEY:
    print("FATAL ERROR: Environment variable OPENAI_API_KEY belum di-set.")
    exit(1) # Keluar jika key tidak ada

# --- Route untuk Generate Image ---
@app.route('/generate-image', methods=['POST'])
def handle_generate_image():
    """Menerima prompt via POST JSON, memanggil OpenAI, mengembalikan URL gambar."""

    # 1. Dapatkan data JSON dari request
    if not request.is_json:
        return jsonify({"error": "Request body harus berupa JSON"}), 400

    data = request.get_json()
    prompt = data.get('prompt') # Ambil 'prompt' dari JSON

    if not prompt:
        return jsonify({"error": "Field 'prompt' tidak ditemukan dalam JSON body"}), 400

    print(f"Menerima request untuk prompt: '{prompt}'") # Logging sederhana

    # 2. Siapkan request ke OpenAI
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "dall-e-3", # Atau model lain jika perlu
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024" # Pastikan size didukung model
    }

    # 3. Panggil API OpenAI
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60) # Tambah timeout
        response.raise_for_status() # Akan raise exception untuk status 4xx/5xx

        # 4. Proses response sukses dari OpenAI
        openai_data = response.json()
        image_url = openai_data.get("data", [{}])[0].get("url")

        if image_url:
            print("Berhasil generate gambar.")
            return jsonify({"image_url": image_url})
        else:
            # Jika struktur response tidak sesuai harapan
            print(f"Struktur response OpenAI tidak sesuai: {openai_data}")
            return jsonify({"error": "Gagal mengekstrak URL gambar dari response OpenAI"}), 500

    except requests.exceptions.HTTPError as http_err:
        # Error dari API OpenAI (misal: 400, 401, 429, 500)
        print(f"HTTP error dari OpenAI: {http_err}")
        print(f"Status Code: {response.status_code}")
        # Coba dapatkan detail error dari response body OpenAI
        try:
            error_details = response.json()
        except ValueError: # Jika response body bukan JSON
            error_details = response.text
        return jsonify({
            "error": "Request ke OpenAI API gagal",
            "status_code": response.status_code,
            "details": error_details
            }), response.status_code # Kembalikan status code asli OpenAI
    except requests.exceptions.RequestException as req_err:
        # Error koneksi/network lainnya
        print(f"Error koneksi saat memanggil OpenAI: {req_err}")
        return jsonify({"error": "Gagal menghubungi OpenAI API"}), 504 # Gateway Timeout
    except Exception as e:
        # Tangkap error tak terduga lainnya
        print(f"Terjadi error tidak terduga: {e}")
        return jsonify({"error": "Internal server error"}), 500

# --- Route dasar untuk cek server ---
@app.route('/')
def index():
    return "Python OpenAI Proxy Server is running!"

# --- Jalankan server ---
if __name__ == '__main__':
    print(f"Menjalankan OpenAI Proxy server di http://0.0.0.0:{LISTEN_PORT}")
    print("Pastikan environment variable OPENAI_API_KEY sudah di-set!")
    # host='0.0.0.0' membuat server bisa diakses dari luar VPS
    # debug=True jangan dipakai di production, hanya untuk development
    app.run(host='0.0.0.0', port=LISTEN_PORT, debug=False)
