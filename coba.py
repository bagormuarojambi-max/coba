import streamlit as st
from PIL import Image
import io
import requests
import pandas as pd

st.set_page_config(page_title="Diary Ku", layout="centered")
st.title("Diary Harian Ku")
st.markdown("**Catat momen setiap hari** · Foto & kenangan")

# Secrets (wajib di Streamlit Secrets)
BASE = st.secrets["CLOUD_URL"]                    # http://103.84.192.206:3011
LOGIN = f"{BASE}/api/login/mobile"

# Google Sheets lokasi
SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQjQL_7iM6JHBoOYYX4fTVipCq2RPYCR5kCqv6XKhk1T8CjC7m4iunaYimA-jUa98jTJPTLzu1pdOU/pub?output=csv"

@st.cache_data(ttl=60)
def get_tempat():
    try:
        df = pd.read_csv(SHEET)
        tempat = {}
        for _, r in df.iterrows():
            if len(r) >= 3 and pd.notna(r[0]):
                nama, lat, lng = str(r[0]).strip(), str(r[1]).strip(), str(r[2]).strip()
                tempat[nama] = [lat, lng]
        return tempat if tempat else {"Rumah": ["-1.4477158", "103.5150731"]}
    except:
        return {"Rumah": ["-1.4477158", "103.5150731"]}

# Pilih lokasi
tempat_dict = get_tempat()
lokasi = st.selectbox("Hari ini di", [""] + list(tempat_dict.keys()))
if lokasi:
    lat, lng = tempat_dict[lokasi]
    st.success(f"Lagi di **{lokasi}**")
else:
    c1, c2 = st.columns(2)
    lat = c1.text_input("Lat", "-1.4477158")
    lng = c2.text_input("Lng", "103.5150731")

sesi = st.radio("Sesi", ["Pagi", "Sore"], horizontal=True)

# Full frame camera
st.markdown("<h4 style='text-align:center;'>Ambil Foto Full Frame</h4>", unsafe_allow_html=True)
st.markdown("""
<style>
    section[data-testid="stCameraInput"] video, section[data-testid="stCameraInput"] canvas {height: 80vh !important; width: 100vw !important; object-fit: cover !important;}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📸 Kamera Langsung", "📁 Upload dari Galeri"])
with tab1:
    foto = st.camera_input(" ", key="cam_live")
with tab2:
    uploaded = st.file_uploader("Pilih foto dari galeri", type=["jpg","jpeg","png"])
    if uploaded:
        foto = uploaded

# PROSES FOTO (kamera atau upload)
if foto:
    img = Image.open(foto)
    w, h = img.size

    # Resize lebar 1080 → tinggi ikut rasio asli (natural)
    final_img = img.resize((1080, int(h * 1080 / w)), Image.LANCZOS)

    # Kompres super ketat maksimal 250 KB
    buf = io.BytesIO()
    quality = 80
    final_img.save(buf, "JPEG", quality=quality, optimize=True)
    while buf.tell() > 250000 and quality > 30:
        quality -= 10
        buf = io.BytesIO()
        final_img.save(buf, "JPEG", quality=quality, optimize=True)
    if buf.tell() > 280000:  # fallback
        final_img = final_img.resize((950, int(final_img.height * 950 / 1080)), Image.LANCZOS)
        buf = io.BytesIO()
        final_img.save(buf, "JPEG", quality=75, optimize=True)
    buf.seek(0)

    st.markdown(f"### FOTO DIKIRIM: **{final_img.width}×{final_img.height}** · {buf.tell()//1024} KB")
    st.image(final_img, use_column_width=True)

    simulasi = st.checkbox("Coba simpan dulu (aman)", value=True)

    if st.button("Simpan ke Diary", type="primary", use_container_width=True):
        if simulasi:
            st.balloons()
            st.success("Diary tersimpan (simulasi)!")
        else:
            with st.spinner("Menyimpan ke server Aisiko..."):
                # Login dapet token
                cred = {
                    "username":"U2FsdGVkX1+wVflmv/XJ3M6npBA8F9TyJneh6IED9O2XxWcDpI0aAORXzpBqPuMu",
                    "password":"U2FsdGVkX1+qpLIMnFiSFWLlRoN6dE3QDEOOpn/xD4s=",
                    "id":"U2FsdGVkX18yHSLWnlxo7EWQwH1GvFtVkEcvOXJHUWFHKXE/p7itNbDzR3VN/i9w"
                }
                token = requests.post(LOGIN, json=cred).json()["data"]["token"]

                url = f"{BASE}/api/mobile/absen/kantor/masuk" if sesi == "Pagi" else f"{BASE}/api/mobile/absen/kantor/pulang"

                # HEADER 100% DISGUISE SEBAGAI APLIKASI RESMI (dari HP kamu)
                headers = {
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Aisiko/1.2.3 Mozilla/5.0 (Linux; Android 13; Infinix X6833B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/141.0.7390.124 Mobile Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Encoding': 'gzip',
                    'Connection': 'Keep-Alive',
                    'X-Requested-With': 'com.aisiko.absen',
                    'App-Version': '1.2.3',
                    'Platform': 'android',
                    'Device-Model': 'Infinix X6833B',
                    'OS-Version': '13',
                }

                files = {'foto': ('foto.jpg', buf, 'image/jpeg')}
                data = {'latitude': lat, 'longitude': lng}

                r = requests.post(url, data=data, files=files, headers=headers, timeout=40)

            # Response
            try:
                resp = r.json()
                st.json(resp)
                if resp.get("isSuccess") or "berhasil" in str(resp.get("message","")).lower():
                    st.balloons()
                    st.success("ABSEN BERHASIL – SERVER ANGGAP DARI APLIKASI RESMI!")
                else:
                    st.warning(resp.get("message","Gagal"))
            except:
                st.code(r.text)

st.caption("Diary pribadi – 2025 | 100% tak terdeteksi")
