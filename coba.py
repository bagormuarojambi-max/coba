import streamlit as st
from PIL import Image
import io
import requests
import pandas as pd

st.set_page_config(page_title="Diary Ku", layout="centered")
st.title("Diary Harian Ku")
st.markdown("**Catat momen setiap hari** · Foto & kenangan")

# --- KREDENSIAL TETAP DI SINI (HARDCODED) ---
BASE = st.secrets.get("CLOUD_URL", "https://api-kantor-kamu.com") # Kalau error, ganti url manual disini
LOGIN = f"{BASE}/api/login/mobile"

# Google Sheets kamu (CSV public)
SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQjQL_7iM6JHBoOYYX4fTVipCq2RPYCR5kCqv6XKhk1T8CjC7m4iunaYimA-jUa98jTJPTLzu1pdOU/pub?output=csv"

@st.cache_data(ttl=60)
def get_tempat():
    try:
        df = pd.read_csv(SHEET)
        tempat = {}
        for _, r in df.iterrows():
            if len(r) >= 3 and pd.notna(r[0]):
                nama = str(r[0]).strip()
                lat = str(r[1]).strip()
                lng = str(r[2]).strip()
                tempat[nama] = [lat, lng]
        return tempat if tempat else {"Rumah": ["-1.4477158", "103.5150731"]}
    except:
        return {"Rumah": ["-1.4477158", "103.5150731"]}

tempat_dict = get_tempat()

lokasi = st.selectbox("Hari ini di", [""] + list(tempat_dict.keys()))
if lokasi:
    lat, lng = tempat_dict[lokasi]
    st.info(f"Lagi di **{lokasi}**")
else:
    c1, c2 = st.columns(2)
    lat = c1.text_input("Lat", "-1.4477158")
    lng = c2.text_input("Lng", "103.5150731")

sesi = st.radio("Sesi", ["Pagi", "Sore"], horizontal=True)
foto = st.camera_input("Foto momen hari ini")

if foto:
    img = Image.open(foto)
    w, h = img.size

    # --- PERBAIKAN LOGIKA FOTO DI SINI ---
    # Logika baru: Cek mana sisi paling panjang, itu yang dijadikan 1080px
    # Sisi lainnya menyesuaikan (keep aspect ratio)
    max_side = 1080 
    
    if w > h: # Landscape (Lebar)
        new_w = max_side
        new_h = int(h * (max_side / w))
    else: # Portrait (Tinggi/Vertikal)
        new_h = max_side
        new_w = int(w * (max_side / h))
        
    final = img.resize((new_w, new_h), Image.LANCZOS)
    # -------------------------------------

    buf = io.BytesIO()
    q = 92
    final.save(buf, "JPEG", quality=q, optimize=True)
    
    # Loop kompresi biar file ringan tapi tetap full frame
    while buf.tell() > 340000 and q > 30:
        q -= 5
        buf = io.BytesIO()
        final.save(buf, "JPEG", quality=q, optimize=True)
    buf.seek(0)

    # Tampilkan preview full column agar terlihat jelas
    st.image(final, caption="Preview foto", use_container_width=True)

    coba_dulu = st.checkbox("Coba simpan dulu (aman)", value=True)

    if st.button("Simpan ke Diary", type="primary", use_container_width=True):
        if coba_dulu:
            st.balloons()
            st.success("Diary tersimpan (simulasi)!")
        else:
            with st.spinner("Menyimpan ke cloud..."):
                # Kredensial hardcoded sesuai permintaan
                cred = {
                    "username":"U2FsdGVkX1+wVflmv/XJ3M6npBA8F9TyJneh6IED9O2XxWcDpI0aAORXzpBqPuMu",
                    "password":"U2FsdGVkX1+qpLIMnFiSFWLlRoN6dE3QDEOOpn/xD4s=",
                    "id":"U2FsdGVkX18yHSLWnlxo7EWQwH1GvFtVkEcvOXJHUWFHKXE/p7itNbDzR3VN/i9w"
                }
                
                try:
                    token = requests.post(LOGIN, json=cred).json()["data"]["token"]
                    url = f"{BASE}/api/mobile/absen/kantor/masuk" if sesi == "Pagi" else f"{BASE}/api/mobile/absen/kantor/pulang"
                    
                    files = {'foto': ('foto.jpg', buf, 'image/jpeg')}
                    r = requests.post(url, data={'latitude':lat,'longitude':lng}, files=files, headers={'authorization':f'Bearer {token}'}, timeout=30)

                    st.subheader("Status Cloud")
                    resp = r.json()
                    st.json(resp, expanded=False)
                    
                    if resp.get("isSuccess") or "berhasil" in str(resp.get("message","")).lower():
                        st.balloons()
                        st.success("Diary tersimpan di cloud!")
                    else:
                        st.warning("Sudah ada catatan hari ini")
                except Exception as e:
                    st.error(f"Error: {e}")
                    if 'r' in locals():
                         st.code(r.text)

st.caption("Aplikasi diary pribadi – 2025")
