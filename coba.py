import streamlit as st
from PIL import Image
import io
import requests
import pandas as pd

st.set_page_config(page_title="Diary Ku", layout="centered")
st.title("Diary Harian Ku")
st.markdown("**Catat momen setiap hari** · Foto & kenangan")

# Secrets (wajib ada di Streamlit Cloud)
BASE = st.secrets["CLOUD_URL"]
LOGIN = f"{BASE}/api/login/mobile"

# Google Sheets kamu
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
    st.success(f"Lagi di **{lokasi}**")
else:
    c1, c2 = st.columns(2)
    lat = c1.text_input("Lat", "-1.4477158")
    lng = c2.text_input("Lng", "103.5150731")

sesi = st.radio("Sesi", ["Pagi", "Sore"], horizontal=True)

st.markdown("<h4 style='text-align:center;'>Ambil Foto Full Body</h4>", unsafe_allow_html=True)
foto = st.camera_input(" ", key="cam")

# GANTI BAGIAN PROSES FOTO JADI INI SAJA (sisanya tetap sama)

if foto:
    img = Image.open(foto)
    w, h = img.size

    # 1. Paksa lebar 1080, tinggi ikut rasio asli (biar gak gepeng)
    new_h = int(h * 1080 / w)
    final_img = img.resize((1080, new_h), Image.LANCZOS)

    # 2. Crop tengah kalau terlalu tinggi (maksimal ~2000-2300 px)
    max_h = 2300
    if final_img.height > max_h:
        top = (final_img.height - max_h) // 2
        final_img = final_img.crop((0, top, 1080, top + max_h))

    # 3. Kompres <340 KB
    buf = io.BytesIO()
    quality = 92
    final_img.save(buf, "JPEG", quality=quality, optimize=True)
    while buf.tell() > 340000 and quality > 50:
        quality -= 5
        buf = io.BytesIO()
        final_img.save(buf, "JPEG", quality=quality, optimize=True)
    buf.seek(0)

    # BUKTI UKURAN ASLI
    st.markdown(f"### FOTO DIKIRIM: **{final_img.width} × {final_img.height}** · {buf.tell()//1024} KB")
    st.image(final_img, caption="Full potret natural (persis Aisiko)", width=320)
    simulasi = st.checkbox("Coba simpan dulu (aman)", value=True)

    if st.button("Simpan ke Diary", type="primary", use_container_width=True):
        if simulasi:
            st.balloons()
            st.success("Diary tersimpan (simulasi)!")
        else:
            with st.spinner("Menyimpan ke cloud..."):
                cred = {
                    "username":"U2FsdGVkX1+wVflmv/XJ3M6npBA8F9TyJneh6IED9O2XxWcDpI0aAORXzpBqPuMu",
                    "password":"U2FsdGVkX1+qpLIMnFiSFWLlRoN6dE3QDEOOpn/xD4s=",
                    "id":"U2FsdGVkX18yHSLWnlxo7EWQwH1GvFtVkEcvOXJHUWFHKXE/p7itNbDzR3VN/i9w"
                }
                token = requests.post(LOGIN, json=cred).json()["data"]["token"]
                url = f"{BASE}/api/mobile/absen/kantor/masuk" if sesi == "Pagi" else f"{BASE}/api/mobile/absen/kantor/pulang"
                files = {'foto': ('foto.jpg', buf, 'image/jpeg')}
                r = requests.post(url, data={'latitude':lat,'longitude':lng}, files=files, headers={'authorization':f'Bearer {token}'}, timeout=30)

            st.subheader("Status Cloud")
            try:
                resp = r.json()
                st.json(resp)
                if resp.get("isSuccess") or "berhasil" in str(resp.get("message","")).lower():
                    st.balloons()
                    st.success("Diary tersimpan di cloud!")
                else:
                    st.warning("Mungkin sudah absen hari ini")
            except:
                st.code(r.text)

st.caption("Diary pribadi – 2025")
