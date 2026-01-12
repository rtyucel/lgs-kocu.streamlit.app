import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os

# --- 1. AYARLAR ---
# Google AI Studio'dan aldığın API Key'i buraya tırnak içine yapıştır
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])



# Sayfa ayarları
st.set_page_config(page_title="LGS Akıllı Koç", page_icon="🎓")

# Müfredat dosyasını yükle
try:
    with open('mufredat.json', 'r', encoding='utf-8') as f:
        mufredat = json.load(f)
except FileNotFoundError:
    st.error("HATA: mufredat.json dosyası bulunamadı! Lütfen aynı klasörde olduğundan emin ol.")
    st.stop()

# Öğrenci takip verisi (Basit JSON veritabanı)
DATA_FILE = 'ogrenci_verisi.json'

def veri_yukle():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def veri_kaydet(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# --- 2. YAPAY ZEKA (GEMINI) ANALİZ FONKSİYONU ---
def analiz_et(image):
    # Yeni Satır:
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # AI'ya referans olması için tüm konuları "Ders - Konu" formatında listeliyoruz
    konu_havuzu = []
    for ders_kodu, konular in mufredat.items():
        ders_adi = ders_kodu.replace("_8", "").upper() # "matematik_8" -> "MATEMATİK"
        for k in konular:
            konu_havuzu.append(f"{ders_adi} : {k['konu']}")
            
    prompt = f"""
    Sen uzman bir LGS öğretmenisin. Görevin bu görseldeki soruyu analiz etmek.
    
    Adımlar:
    1. Sorunun hangi derse (Matematik, Fen, Türkçe vb.) ait olduğunu anla.
    2. Sorunun konusunu tespit et.
    3. Aşağıdaki referans listesinden EN UYGUN olanı seç.
    
    Referans Listesi: {konu_havuzu}
    
    Cevabı SADECE şu formatta ver (Başka hiçbir şey yazma):
    SONUC: [Seçtiğin Referans Listesindeki İsim]
    """
    
    with st.spinner('Yapay zeka soruyu inceliyor, müfredatla eşleştiriyor...'):
        response = model.generate_content([prompt, image])
        return response.text.replace("SONUC: ", "").strip()

# --- 3. ARAYÜZ TASARIMI ---
st.title("🎓 LGS Akıllı Soru Koçu")
st.write("Fotoğrafını yükle, hangi konuda eksiğin var hemen bulalım.")

# Kamera ve Dosya Yükleme Seçeneği
tab1, tab2 = st.tabs(["📸 Fotoğraf Çek", "📂 Galeriden Yükle"])

img_file = None
with tab1:
    cam_img = st.camera_input("Soru Çek")
    if cam_img: img_file = cam_img
with tab2:
    upl_img = st.file_uploader("Resim Seç", type=['png', 'jpg', 'jpeg'])
    if upl_img: img_file = upl_img

if img_file:
    image = Image.open(img_file)
    st.image(image, caption='Analiz Edilecek Soru', width=300)
    
    if st.button("🚀 Analizi Başlat", type="primary"):
        # Analiz işlemi
        tespit_edilen = analiz_et(image)
        st.session_state['son_tespit'] = tespit_edilen
        st.session_state['analiz_yapildi'] = True

# Analiz sonrası işlemler
if 'analiz_yapildi' in st.session_state and st.session_state['analiz_yapildi']:
    tespit = st.session_state['son_tespit']
    
    st.divider()
    st.success(f"📌 Tespit Edilen Konu: **{tespit}**")
    
    st.write("Bu soruyu doğru çözdün mü?")
    col1, col2 = st.columns(2)
    
    if col1.button("✅ Doğru Yaptım"):
        st.balloons()
        st.info("Harika! Bu konuyu pekiştiriyorsun.")
        st.session_state['analiz_yapildi'] = False

    if col2.button("❌ Yanlış / Boş"):
        # Veritabanına kaydet
        data = veri_yukle()
        if tespit not in data:
            data[tespit] = 0
        data[tespit] += 1
        veri_kaydet(data)
        
        st.error(f"Sorun değil. '{tespit}' konusunda toplam hatan: {data[tespit]}")
        
        # 3 Hatadan fazla ise video öner
        if data[tespit] >= 3:
            st.warning("⚠️ Bu konuda eksiklerin birikti. İşte senin için bir ders videosu:")
            
            # Video linkini JSON'dan bulma
            video_url = "https://youtube.com" # Varsayılan
            
            # Tespit edilen stringi parçala: "MATEMATİK : Üslü İfadeler" -> Konu: "Üslü İfadeler"
            aranan_konu = tespit.split(" : ")[-1]
            
            # JSON içinde ara
            found = False
            for ders in mufredat:
                for icerik in mufredat[ders]:
                    if icerik['konu'] == aranan_konu:
                        video_url = icerik['video_link']
                        found = True
                        break
                if found: break
            
            st.markdown(f"👉 **[Konu Anlatımını İzlemek İçin Tıkla]({video_url})**")
            
        st.session_state['analiz_yapildi'] = False