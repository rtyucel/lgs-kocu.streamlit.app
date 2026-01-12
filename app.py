import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. AYARLAR & BAĞLANTILAR ---

# API Key'i Secrets'tan al
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Sayfa ayarları
st.set_page_config(page_title="LGS Akıllı Koç", page_icon="🎓")

# Google Sheets Bağlantısı
def get_google_sheet():
    # Secrets'tan bilgileri alıp bir sözlük (dictionary) oluşturuyoruz
    creds_dict = dict(st.secrets["service_account"])
    
    # Bağlantıyı kur
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Dosyanı aç (Buraya kendi oluşturduğun Sheet adını tam olarak yaz)
    sheet = client.open("LGS_Takip_Sistemi").sheet1
    return sheet

# Veri Okuma Fonksiyonu (Sheets'ten)
def veri_getir():
    try:
        sheet = get_google_sheet()
        # Tüm kayıtları al
        records = sheet.get_all_records()
        # { 'Konu': HataSayisi } formatına çevir
        data = {}
        for row in records:
            data[row['Konu']] = row['Hata_Sayisi']
        return data
    except Exception as e:
        st.error(f"Veri okunurken hata: {e}")
        return {}

# Veri Kaydetme Fonksiyonu (Sheets'e)
def veri_guncelle(konu):
    try:
        sheet = get_google_sheet()
        # Konu zaten var mı ara?
        cell = sheet.find(konu)
        
        if cell:
            # Varsa yanındaki hücreyi (Hata Sayısı) al ve 1 artır
            current_val = int(sheet.cell(cell.row, cell.col + 1).value)
            sheet.update_cell(cell.row, cell.col + 1, current_val + 1)
        else:
            # Yoksa en alta yeni satır ekle
            sheet.append_row([konu, 1])
            
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

# Müfredat dosyasını yükle
try:
    with open('mufredat.json', 'r', encoding='utf-8') as f:
        mufredat = json.load(f)
except FileNotFoundError:
    st.error("mufredat.json bulunamadı.")
    st.stop()

# --- 2. YAPAY ZEKA ---
def analiz_et(image):
    model = genai.GenerativeModel('gemini-3-flash-preview') # Yeni modelin
    
    konu_havuzu = []
    for ders_kodu, konular in mufredat.items():
        ders_adi = ders_kodu.replace("_8", "").upper()
        for k in konular:
            konu_havuzu.append(f"{ders_adi} : {k['konu']}")
            
    prompt = f"""
    Sen LGS öğretmenisin. Görseli analiz et.
    Ders ve Konuyu tespit et.
    Referans Listesi: {konu_havuzu}
    Cevap Formatı: SONUC: [Seçim]
    """
    
    with st.spinner('Analiz ediliyor...'):
        response = model.generate_content([prompt, image])
        return response.text.replace("SONUC: ", "").strip()

# --- 3. ARAYÜZ ---
st.title("🎓 LGS Bulut Koçu")
st.caption("Verileriniz Google Sheets üzerinde saklanmaktadır.")

tab1, tab2 = st.tabs(["📸 Fotoğraf Çek", "📊 İstatistiklerim"])

with tab1:
    img_file = st.camera_input("Soru Çek")
    # (Galeriden yükleme kısmını sadeleştirdim, istersen ekleyebilirsin)
    
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=300)
        
        if st.button("🚀 Analiz Et", type="primary"):
            tespit = analiz_et(image)
            st.session_state['son_tespit'] = tespit
            st.session_state['analiz_yapildi'] = True

    if 'analiz_yapildi' in st.session_state and st.session_state['analiz_yapildi']:
        tespit = st.session_state['son_tespit']
        st.divider()
        st.success(f"📌 Tespit: **{tespit}**")
        
        col1, col2 = st.columns(2)
        if col1.button("✅ Doğru"):
            st.balloons()
            st.session_state['analiz_yapildi'] = False
            
        if col2.button("❌ Yanlış"):
            with st.spinner("Veritabanına işleniyor..."):
                veri_guncelle(tespit) # Sheets'e yazıyor
            st.warning("Hata kaydedildi.")
            
            # Güncel hatayı okuyup video önerme mantığı buraya eklenebilir
            st.session_state['analiz_yapildi'] = False

with tab2:
    st.subheader("Hata Karnesi")
    if st.button("Verileri Yenile"):
        veriler = veri_getir()
        if veriler:
            st.bar_chart(veriler)
        else:
            st.info("Henüz hata kaydı yok.")