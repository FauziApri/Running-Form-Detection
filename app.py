import base64
import os
import tempfile
import streamlit as st

from biomechanics import RunningBiomechanicsAnalyzer
from knowledge_base import evaluate_running_form

st.set_page_config(
    page_title="RunFormers - Analisis Form Lari",
    page_icon=":material/directions_run:",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_icon_uri(icon_name: str) -> str:
    if os.path.exists(icon_name):
        ext = os.path.splitext(icon_name)[1].lower()
        mime = "image/svg+xml" if ext == ".svg" else "image/png"
        with open(icon_name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    base_name = os.path.splitext(os.path.basename(icon_name))[0]
    for ext, mime in [(".svg", "image/svg+xml"), (".png", "image/png"), (".webp", "image/webp")]:
        filepath = os.path.join("assets", "icons", base_name + ext)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    return ""

def render_icon(icon_name: str, size: int = 22) -> str:
    uri = get_icon_uri(icon_name)
    if not uri:
        return ""
    return f'<img src="{uri}" width="{size}" height="{size}" style="object-fit:contain; display:block;" />'

# Muat file CSS eksternal
with open("assets/style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# State navigasi halaman dan data hasil analisis (kosong di awal)
if "page" not in st.session_state:
    st.session_state.page = "Beranda"
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

# --- MODAL PANDUAN VIDEO ---
@st.dialog("Panduan Pengambilan Video Lari")
def show_guide_dialog():
    st.markdown("""
    Agar deteksi pose **MediaPipe** dan perhitungan sudut biomekanika akurat:
    1. **Sudut Pengambilan:** Rekam dari **samping (side-view)** sejajar lintasan lari.
    2. **Framing Penuh:** Pastikan seluruh tubuh dari kepala hingga ujung sepatu terlihat jelas dalam frame.
    3. **Pencahayaan & Latar:** Gunakan pencahayaan terang dengan latar belakang yang kontras dengan pakaian lari.
    4. **Durasi Ideal:** Gunakan klip video berdurasi **5–30 detik** dalam format `.MP4`, `.MKV`, `.AVI`, atau `.MOV`.
    """)

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.markdown('<div class="brand-title"><span class="brand-run">Run</span><span class="brand-formers">Formers</span></div>', unsafe_allow_html=True)

    active_bg = "#333D4F"
    active_color = "#22C58B"
    inactive_color = "#FFFFFF"
    beranda_active = st.session_state.page == "Beranda"

    # Cukup tulis nama filenya saja tanpa .png/.svg (sesuaikan dengan nama file di assets/icons/)
    icon_beranda = get_icon_uri("beranda")
    icon_analisis = get_icon_uri("analisis")
    icon_upload = get_icon_uri("upload")

    st.markdown(f"""
    <style>
    .st-key-nav_beranda button,
    .st-key-nav_analisis button {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 10px;
    }}

    .st-key-nav_beranda button::before,
    .st-key-nav_analisis button::before {{
        content: "";
        display: inline-block;
        width: 18px;
        height: 18px;
        flex-shrink: 0;
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}

    .st-key-nav_beranda button {{
        background-color: {active_bg if beranda_active else "transparent"} !important;
        color: {active_color if beranda_active else inactive_color} !important;
    }}
    .st-key-nav_beranda button::before {{
        background-image: url("{icon_beranda}");
    }}

    .st-key-nav_analisis button {{
        background-color: {active_bg if not beranda_active else "transparent"} !important;
        color: {active_color if not beranda_active else inactive_color} !important;
    }}
    .st-key-nav_analisis button::before {{
        background-image: url("{icon_analisis}");
    }}

    /* Ikon upload pada area unggah video */
    [data-testid="stFileUploaderDropzoneInstructions"]::before {{
        content: "";
        width: 64px;
        height: 64px;
        margin-bottom: 0.9rem;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.16);
        background-image: url("{icon_upload}");
        background-position: center;
        background-repeat: no-repeat;
        background-size: 30px 30px;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
        transition: transform 0.2s ease;
    }}

    [data-testid="stFileUploaderDropzone"]:hover [data-testid="stFileUploaderDropzoneInstructions"]::before {{
        transform: translateY(-2px);
    }}
    </style>
    """, unsafe_allow_html=True)

    if st.button("Beranda", key="nav_beranda"):
        st.session_state.page = "Beranda"
        st.rerun()

    if st.button("Analisis", key="nav_analisis"):
        st.session_state.page = "Analisis"
        st.rerun()
        
# --- HALAMAN 1: BERANDA (MAIN PAGE) ---
if st.session_state.page == "Beranda":
    uploaded_file = st.file_uploader(
        "UPLOAD VIDEO FILE (.MP4, .MKV, .AVI, .MOV)",
        type=["mp4", "mkv", "avi", "mov"],
        label_visibility="collapsed"
    )

    st.markdown("""
    <script>
    const span = window.parent.document.querySelector('[data-testid="stFileUploaderDropzoneInstructions"] span');
    const small = window.parent.document.querySelector('[data-testid="stFileUploaderDropzoneInstructions"] small');
    if (span) span.innerText = "UPLOAD VIDEO FILE";
    if (small) small.innerText = "(.MP4, .MKV, .AVI, .MOV)";
    </script>
    """, unsafe_allow_html=True)

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.read())
            raw_video_path = tmp.name

        with st.spinner("Menganalisis postur, langkah kaki, dan ayunan lengan..."):
            try:
                analyzer = RunningBiomechanicsAnalyzer(model_path="models/pose_landmarker_full.task")
                metrics, output_video_path = analyzer.process_video(raw_video_path)
                st.session_state.video_path = output_video_path
                st.session_state.analysis_results = evaluate_running_form(metrics)

                st.session_state.page = "Analisis"
                st.rerun()
            except Exception as e:
                st.error(f"Terjadi kendala saat menganalisis video: {e}")
                
        st.session_state.page = "Analisis"
        st.rerun()

    col_l, col_mid, col_r = st.columns([2, 1, 2])
    with col_mid:
        if st.button("Lihat Panduan", use_container_width=True):
            show_guide_dialog()

    st.markdown('<div class="section-heading">Apa yang bisa dianalisis?</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(f'<div class="feature-card"><div class="feature-header"><div class="feature-icon-box">{render_icon("assets/icons/postur_sm.png", 20)}</div><p class="feature-title">Postur Tubuh</p></div><p class="feature-desc">Cek posisi badan saat berlari (tegak atau membungkuk)</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="feature-card"><div class="feature-header"><div class="feature-icon-box">{render_icon("assets/icons/langkah_sm.png", 20)}</div><p class="feature-title">Langkah Kaki</p></div><p class="feature-desc">Analisis panjang langkah dan frekuensi (stride dan cadence)</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="feature-card"><div class="feature-header"><div class="feature-icon-box">{render_icon("assets/icons/lengan_sm.png", 20)}</div><p class="feature-title">Gerakan Lengan</p></div><p class="feature-desc">Pastikan sudut dan ayunan tangan seimbang dan rileks</p></div>', unsafe_allow_html=True)
    
# --- HALAMAN 2: ANALISIS (ANALYSIS PAGE) ---
elif st.session_state.page == "Analisis":
    has_video = (
        st.session_state.video_path is not None
        and os.path.exists(st.session_state.video_path)
        and st.session_state.analysis_results is not None
    )

    col_video, col_result = st.columns([1.15, 1], gap="large")

    with col_video:
        st.markdown('<div class="preview-wrapper"><div class="preview-label">Video Preview</div>', unsafe_allow_html=True)
        if has_video:
            st.video(st.session_state.video_path)
        else:
            st.info("Belum ada video yang diunggah. Silakan unggah video di menu Beranda.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_result:
        st.markdown('<div class="analysis-heading">HASIL ANALISIS</div>', unsafe_allow_html=True)

        if has_video:
            res = st.session_state.analysis_results
        else:
            res = {
                "postur": {
                    "level": "neutral",
                    "status": "Belum dianalisis",
                    "advice": "Unggah video lari untuk mengecek kemiringan postur tubuh."
                },
                "langkah": {
                    "level": "neutral",
                    "status": "Belum dianalisis",
                    "advice": "Unggah video lari untuk mengukur jarak langkah (stride)."
                },
                "lengan": {
                    "level": "neutral",
                    "status": "Belum dianalisis",
                    "advice": "Unggah video lari untuk mengevaluasi sudut ayunan lengan."
                }
            }

        cards_config = [
            ("Postur Tubuh", render_icon("assets/icons/postur_sm.png", 44), res["postur"]),
            ("Langkah Kaki", render_icon("assets/icons/langkah_sm.png", 44), res["langkah"]),
            ("Gerakan Lengan", render_icon("assets/icons/lengan_sm.png", 44), res["lengan"]),
        ]

        badge_symbol = {
            "ideal": "✓",
            "danger": "!",
            "warning": "▲",
            "neutral": "—"
        }

        for title, icon, data in cards_config:
            lvl = data["level"]
            symbol = badge_symbol.get(lvl, "—")
            st.markdown(
                f'<div class="result-card card-{lvl}">'
                f'<div class="result-left">'
                f'<div class="result-silhouette">{icon}</div>'
                f'<div>'
                f'<p class="result-title">{title}</p>'
                f'<p class="result-status">{data["status"]}</p>'
                f'<p class="result-advice">{data["advice"]}</p>'
                f'</div></div>'
                f'<div class="status-badge badge-{lvl}">{symbol}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        b_left, b_mid, b_right = st.columns([1, 1.2, 1])
        with b_mid:
            btn_label = "Selesai" if has_video else "Unggah Video"
            if st.button(btn_label, use_container_width=True):
                st.session_state.video_path = None
                st.session_state.analysis_results = None
                st.session_state.page = "Beranda"
                st.rerun()