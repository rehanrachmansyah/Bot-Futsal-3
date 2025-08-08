from flask import Flask, request, jsonify
import requests
import json
import os # Import modul os untuk mengakses environment variables

app = Flask(__name__)

# Mengambil INSTANCE_ID dan TOKEN dari environment variables
# Pastikan Anda telah mengatur variabel ini di Railway Dashboard Anda
INSTANCE_ID = os.environ.get('ULTRAMSG_INSTANCE_ID')
TOKEN = os.environ.get('ULTRAMSG_TOKEN')

# Pastikan INSTANCE_ID dan TOKEN telah diatur
if not INSTANCE_ID or not TOKEN:
    print("Error: ULTRAMSG_INSTANCE_ID atau ULTRAMSG_TOKEN tidak ditemukan di environment variables.")
    # Anda bisa memilih untuk keluar atau menangani error ini dengan cara lain
    # Untuk deployment, ini akan menyebabkan aplikasi gagal startup jika variabel tidak ada.

# Path untuk file database jadwal.json
JADWAL_FILE = 'jadwal.json'

# Load data jadwal
def load_jadwal():
    try:
        with open(JADWAL_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {JADWAL_FILE} tidak ditemukan. Membuat file baru dengan jadwal kosong.")
        # Inisialisasi jadwal jika file tidak ada
        initial_jadwal = {
            "18.00": None,
            "19.00": None,
            "20.00": None,
            "21.00": None
        }
        save_jadwal(initial_jadwal)
        return initial_jadwal
    except json.JSONDecodeError:
        print(f"Error membaca file {JADWAL_FILE}. Memulai dengan jadwal kosong.")
        initial_jadwal = {
            "18.00": None,
            "19.00": None,
            "20.00": None,
            "21.00": None
        }
        save_jadwal(initial_jadwal)
        return initial_jadwal


# Simpan data jadwal
def save_jadwal(jadwal):
    with open(JADWAL_FILE, 'w') as f:
        json.dump(jadwal, f, indent=4)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    print("DATA MASUK:", payload)

    # Pastikan payload memiliki struktur yang diharapkan
    if not payload or 'data' not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    msg_data = payload['data']
    msg = msg_data.get('body', '').lower()
    sender = msg_data.get('from', '')

    if not msg or not sender:
        return jsonify({"error": "Missing 'body' or 'from' in data"}), 400

    # Load jadwal
    jadwal = load_jadwal()
    response_text = ""

    if "jadwal" in msg:
        response_text = "📅 Jadwal tersedia:\n"
        for jam in sorted(jadwal.keys()): # Mengurutkan jam agar tampilan lebih rapi
            status = "✅ Tersedia" if not jadwal[jam] else f"❌ Sudah dibooking oleh {jadwal[jam]}"
            response_text += f"- {jam}: {status}\n"

    elif "book" in msg:
        booked = False
        for jam in sorted(jadwal.keys()):
            if jam in msg and not jadwal[jam]:
                # Mengekstrak nama tim setelah "atas nama"
                parts = msg.split("atas nama")
                if len(parts) > 1:
                    nama_tim = parts[-1].strip().title()
                    if nama_tim: # Pastikan nama tim tidak kosong
                        jadwal[jam] = nama_tim
                        save_jadwal(jadwal)
                        response_text = f"✅ Booking berhasil untuk jam {jam} atas nama {nama_tim}!"
                        booked = True
                        break
                else:
                    response_text = "❌ Format booking salah. Gunakan: *book [jam] atas nama [Nama Tim Anda]*"
                    booked = True # Untuk mencegah masuk ke else di bawah
                    break
        if not booked:
            response_text = "❌ Jam tersebut tidak tersedia atau sudah dibooking."

    else:
        response_text = "⚽ Halo! Ketik *jadwal* untuk melihat jadwal lapangan,\natau ketik *book 18.00 atas nama Tim Kamu* untuk booking."

    # Kirim ke WhatsApp
    send_message(sender, response_text)
    return jsonify({"status": "ok"})


def send_message(to, message):
    # URL UltraMsg API
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "to": to,
        "body": message
    }
    # Mengirim permintaan POST ke UltraMsg API
    try:
        response = requests.post(url, json=payload, headers=headers, params={"token": TOKEN})
        response.raise_for_status() # Akan memunculkan HTTPError untuk status kode 4xx/5xx
        print(f"Pesan berhasil dikirim ke {to}. Respon UltraMsg: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengirim pesan ke {to}: {e}")
        # Anda bisa menambahkan logging atau penanganan error yang lebih canggih di sini

@app.route('/lihat-jadwal', methods=['GET'])
def lihat_jadwal():
    TOKEN_AMAN = os.environ.get("JADWAL_ACCESS_TOKEN")
    token = request.args.get('token')

    if not TOKEN_AMAN or token != TOKEN_AMAN:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        jadwal = load_jadwal()
        return jsonify(jadwal)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#komen

if __name__ == '__main__':
    # Mengambil port dari environment variable PORT yang disediakan oleh Railway
    # Default ke 5000 jika tidak ditemukan (untuk pengembangan lokal)
    port = int(os.environ.get("PORT", 5000))
    # Menjalankan aplikasi di semua antarmuka jaringan dan menonaktifkan debug mode
    app.run(host='0.0.0.0', port=port, debug=False)
