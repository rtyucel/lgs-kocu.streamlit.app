import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- 1. TASARIM VE AYARLAR ---
st.set_page_config(
    page_title="LGS Pro",
    page_icon="🚀",
    layout="centered", # Mobilde daha derli toplu durur
    initial_sidebar_state="collapsed"
)

# Özel CSS ile İstenmeyen Yazıları Gizleme ve Butonları Güzelleştirme
st.markdown("""
<style>
    /* Üstteki renkli çizgiyi ve footer'ı gizle */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Butonları biraz daha geniş ve yuvarlak yap */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3em;
        font-weight: bold;
    }
    
    /* Kamera alanını çerçeve içine al */
    .stCameraInput {
        border: 2px solid #f0f2f6;
        border-radius: 15px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. BAĞLANTILAR (AYNI KALDI) ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def get_sheet():
    creds_dict = dict(st.secrets["service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("LGS_Takip_Sistemi").sheet1

def hata_ekle(isim, konu):
    try:
        sh = get_sheet()
        data = sh.get_all_values()
        satir_no = 0
        mevcut_hata = 0
        for i, row in enumerate(data[1:], start=2):
            if row[0] == isim and row[1] == konu:
                satir_no = i
                mevcut_hata = int(row[2])
                break
        if satir_no > 0:
            sh.update_cell(satir_no, 3, mevcut_hata + 1)
        else:
            sh.append_row([isim, konu, 1])
    except Exception as e:
        st.error(f"Hata: {e}")

def istatistik_getir(isim):
    try:
        sh = get_sheet()
        records = sh.get_all_records()
        ders_bazli_veri = {}
        toplam_hata = 0
        
        for row in records:
            if row['İsim'] == isim:
                tam_konu = row['Konu']
                hata = row['Hata_Sayisi']
                toplam_hata += hata
                
                if " : " in tam_konu:
                    ders, konu = tam_konu.split(" : ")
                else:
                    ders = "DİĞER"
                    konu = tam_konu
                
                if ders not in ders_bazli_veri:
                    ders_bazli_veri[ders] = {}
                ders_bazli_veri[ders][konu] = hata
                
        return ders_bazli_veri, toplam_hata
    except:
        return {}, 0

try:
    with open('mufredat.json', 'r', encoding='utf-8') as f:
        mufredat = json.load(f)
except:
    st.stop()

def analiz_et(image):
    model = genai.GenerativeModel('gemini-3-flash-preview')
    konu_havuzu = []
    for ders, konular in mufredat.items():
        d_adi = ders.replace("_8", "").upper()
        for k in konular:
            konu_havuzu.append(f"{d_adi} : {k['konu']}")
    prompt = f"Görseldeki sorunun dersini/konusunu bul. Liste: {konu_havuzu}. Format: SONUC: [Seçim]"
    response = model.generate_content([prompt, image])
    return response.text.replace("SONUC: ", "").strip()

# --- 3. AKIŞ KONTROLÜ (SESSION STATE) ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

# --- EKRAN 1: GİRİŞ EKRANI (Mobil Uyumlu) ---
if not st.session_state['giris_yapildi']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/3429/3429149.png", width=100) # Logo
        st.markdown("<h2 style='text-align: center;'>LGS Koçum</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Seni tanımamız için ismini gir</p>", unsafe_allow_html=True)
        
        isim_giris = st.text_input("Adın Soyadın", label_visibility="collapsed", placeholder="Örn: Ali Yılmaz")
        
        if st.button("🚀 Başla"):
            if isim_giris:
                st.session_state['kullanici_adi'] = isim_giris.title()
                st.session_state['giris_yapildi'] = True
                st.rerun() # Sayfayı yenile ve ana ekrana geç
            else:
                st.toast("Lütfen ismini yaz!", icon="⚠️")

# --- EKRAN 2: ANA UYGULAMA ---
else:
    kullanici = st.session_state['kullanici_adi']
    
    # Üst Bar (Çıkış Yap butonu ile)
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"👋 Selam, {kullanici.split()[0]}")
    if c2.button("Çıkış"):
        st.session_state['giris_yapildi'] = False
        st.rerun()

    # Sekmeler (Daha modern ikonlu)
    tab1, tab2 = st.tabs(["📸 Soru Çöz", "📊 Analiz"])

    # --- TAB 1: KAMERA ALANI ---
    with tab1:
        st.info("Sadece soruyu görecek şekilde fotoğrafı çek.")
        
        # Kamera input (Tam genişlikte olacak)
        img = st.camera_input("Kamera", label_visibility="collapsed")
        
        if img:
            # Resmi göster (Biraz küçültülmüş ve ortalanmış)
            st.image(img, caption="Çekilen Soru", use_column_width=True)
            
            if st.button("✨ Yapay Zekaya Sor", type="primary"):
                with st.spinner("Soru taranıyor..."):
                    tespit = analiz_et(Image.open(img))
                    st.session_state['tespit'] = tespit
                    st.session_state['onay_bekliyor'] = True
            
            # Analiz Sonucu Kartı
            if st.session_state.get('onay_bekliyor'):
                st.markdown("---")
                st.markdown(f"""
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff;">
                    <h4 style="margin:0; color: #007bff;">Tespit Edilen Konu:</h4>
                    <p style="font-size: 18px; font-weight: bold; margin:0;">{st.session_state['tespit']}</p>
                </div>
                <br>
                """, unsafe_allow_html=True)
                
                col_a, col_b = st.columns(2)
                if col_a.button("✅ Doğru"):
                    st.toast("Harika! Doğru cevap.", icon="🎉")
                    st.balloons()
                    st.session_state['onay_bekliyor'] = False
                    time.sleep(1)
                    st.rerun() # Kamerayı sıfırla
                    
                if col_b.button("❌ Yanlış"):
                    hata_ekle(kullanici, st.session_state['tespit'])
                    st.toast("Kaydedildi. Konu tekrarı yap!", icon="📝")
                    st.session_state['onay_bekliyor'] = False
                    time.sleep(1)
                    st.rerun()

    # --- TAB 2: İSTATİSTİK ALANI ---
    with tab2:
        veriler, toplam_hata = istatistik_getir(kullanici)
        
        if veriler:
            # Dashboard Görünümü (Metricler)
            m1, m2 = st.columns(2)
            m1.metric("Toplam Hata", f"{toplam_hata}", delta_color="inverse")
            m2.metric("Ders Sayısı", f"{len(veriler)}")
            
            st.divider()
            
            ders_secim = st.pills("Ders Seç", list(veriler.keys()), selection_mode="single")
            
            if ders_secim:
                st.subheader(f"{ders_secim} Analizi")
                st.bar_chart(veriler[ders_secim])
                
                # Video Önerisi
                secili_ders_verisi = veriler[ders_secim]
                en_kotu_konu = max(secili_ders_verisi, key=secili_ders_verisi.get)
                
                if secili_ders_verisi[en_kotu_konu] >= 3:
                    with st.expander(f"⚠️ {en_kotu_konu} - Tavsiye Var!", expanded=True):
                        st.write(f"Bu konuda **{secili_ders_verisi[en_kotu_konu]} yanlışın** var.")
                        st.markdown(f"[👉 YouTube Dersi İzle](https://www.youtube.com/results?search_query=8.sinif+{en_kotu_konu.replace(' ', '+')})")
            else:
                st.info("Detaylı grafik görmek için yukarıdan bir ders seç.")
                
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/7486/7486744.png", width=100)
            st.markdown("<h3 style='text-align: center;'>Veri Yok</h3>", unsafe_allow_html=True)
            st.info("Henüz hiç yanlış yapmadın veya sisteme giriş yapmadın. Soru çözmeye başla!")