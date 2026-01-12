import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- AYARLAR ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
st.set_page_config(page_title="LGS Akıllı Koç", page_icon="🎓")

# --- SHEET FONKSİYONLARI ---
def get_sheet():
    creds_dict = dict(st.secrets["service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("LGS_Takip_Sistemi").sheet1

def hata_ekle(isim, konu):
    try:
        sh = get_sheet()
        data = sh.get_all_values() # Tüm tabloyu çek
        
        # Öğrencinin bu konuda daha önce hatası var mı bulmaya çalış
        satir_no = 0
        mevcut_hata = 0
        
        # Tabloyu tarıyoruz (Başlık satırını atla)
        for i, row in enumerate(data[1:], start=2):
            # Eğer İSİM ve KONU eşleşiyorsa
            if row[0] == isim and row[1] == konu:
                satir_no = i
                mevcut_hata = int(row[2])
                break
        
        if satir_no > 0:
            # Varsa güncelle
            sh.update_cell(satir_no, 3, mevcut_hata + 1)
        else:
            # Yoksa yeni satır ekle
            sh.append_row([isim, konu, 1])
            
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def istatistik_getir(isim):
    try:
        sh = get_sheet()
        records = sh.get_all_records()
        
        kisisel_veri = {}
        # Sadece giriş yapan ismin verilerini süz
        for row in records:
            if row['İsim'] == isim: # Excel başlığın 'İsim' olmalı
                kisisel_veri[row['Konu']] = row['Hata_Sayisi']
        return kisisel_veri
    except Exception as e:
        return {}

# --- MÜFREDAT YÜKLEME ---
try:
    with open('mufredat.json', 'r', encoding='utf-8') as f:
        mufredat = json.load(f)
except:
    st.stop()

# --- AI ANALİZ ---
def analiz_et(image):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    konu_havuzu = []
    for ders, konular in mufredat.items():
        d_adi = ders.replace("_8", "").upper()
        for k in konular:
            konu_havuzu.append(f"{d_adi} : {k['konu']}")
            
    prompt = f"Görseldeki LGS sorusunun dersini ve konusunu bul. Liste: {konu_havuzu}. Sadece formatı yaz: SONUC: [Seçim]"
    response = model.generate_content([prompt, image])
    return response.text.replace("SONUC: ", "").strip()

# --- ARAYÜZ ---
st.title("🎓 LGS Bulut Koçu")

# YAN MENÜ: GİRİŞ EKRANI
with st.sidebar:
    st.header("Öğrenci Girişi")
    kullanici_adi = st.text_input("Adın Soyadın:", placeholder="Örn: Ali Yılmaz")
    
    if kullanici_adi:
        st.success(f"Hoş geldin, {kullanici_adi} 👋")
    else:
        st.warning("Lütfen işlem yapmak için adını gir.")
        st.stop() # Ad girilmezse uygulama burada durur

# ANA EKRAN
tab1, tab2 = st.tabs(["📸 Soru Yükle", "📊 Karnem"])

with tab1:
    img = st.camera_input("Fotoğraf Çek")
    if img:
        st.image(img, width=300)
        if st.button("Analiz Et"):
            tespit = analiz_et(Image.open(img))
            st.session_state['tespit'] = tespit
            st.session_state['onay'] = True

    if st.session_state.get('onay'):
        tespit = st.session_state['tespit']
        st.info(f"Konu: **{tespit}**")
        
        c1, c2 = st.columns(2)
        if c1.button("✅ Doğru"):
            st.balloons()
            st.session_state['onay'] = False
            
        if c2.button("❌ Yanlış"):
            with st.spinner("Kaydediliyor..."):
                hata_ekle(kullanici_adi, tespit) # İsimle beraber kaydet
            st.success("Hata hanene işlendi.")
            st.session_state['onay'] = False

with tab2:
    st.subheader(f"{kullanici_adi} - Hata İstatistiği")
    veriler = istatistik_getir(kullanici_adi)
    
    if veriler:
        st.bar_chart(veriler)
        
        # Basit öneri sistemi
        en_cok_hata = max(veriler, key=veriler.get)
        if veriler[en_cok_hata] >= 3:
            st.warning(f"⚠️ '{en_cok_hata}' konusunda {veriler[en_cok_hata]} yanlışın var. Konu tekrarı yapmalısın!")
    else:
        st.write("Henüz kaydedilmiş bir verin yok.")