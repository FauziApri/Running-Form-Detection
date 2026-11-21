import os
import tempfile
import streamlit as st
from biomechanics import RunningBiomechanicsAnalyzer
from knowledge_base import RunningFormKnowledgeBase


st.set_page_config(
    page_title="RunFormers - Running Form Detection",
    page_icon="🏃",
    layout="wide"
)

# Styling kartu hasil agar menyerupai wireframe RunFormers
st.markdown("""
<style>
    .result-card {
        padding: 1.1rem 1.25rem;
        border-radius: 12px;
        margin-bottom: 0.9rem;
        border-left: 6px solid #ccc;
        background-color: #f8f9fa;
        color: #1f2937;
    }
    .card-good {
        border-left-color: #16a34a;
        background-color: #f0fdf4;
    }
    .card-warning {
        border-left-color: #d97706;
        background-color: #fffbeb;
    }
    .card-danger {
        border-left-color: #dc2626;
        background-color: #fef2f2;
    }
    .card-category {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #4b5563;
        margin-bottom: 0.2rem;
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .card-advice {
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }
    .card-cf {
        font-size: 0.8rem;
        color: #6b7280;
    }
</style>
""", unsafe_allow_html=True)

# Header & Navigasi
col_logo, col_nav = st.columns([3, 2])
with col_logo:
    st.title("🏃 RunFormers")
    st.caption("Sistem Berbasis Pengetahuan untuk Evaluasi Teknik Lari")
with col_nav:
    st.write("")
    page = st.radio(
        "Navigasi",
        ["Beranda", "Analisis"],
        horizontal=True,
        label_visibility="collapsed"
    )

st.divider()

# =========================================================
# HALAMAN 1: BERANDA
# =========================================================
if page == "Beranda":
    st.subheader("Evaluasi Teknik Lari Anda Secara Otomatis")
    st.write(
        "Unggah video rekaman lari tampak samping untuk mendapatkan evaluasi posisi badan, "
        "efisiensi langkah kaki, dan keseimbangan ayunan lengan berbasis aturan biomekanika."
    )

    st.markdown("### Apa yang bisa dianalisis?")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.info("**1. Postur Tubuh**\n\nCek posisi kemiringan badan saat berlari (terlalu tegak, condong ideal 5°–15°, atau membungkuk).")
        with st.expander("Lihat Panduan Postur"):
            st.write("Rekam dari arah samping (side-view) sejajar pinggul agar sudut bahu-pinggul terbaca akurat.")

    with c2:
        st.info("**2. Langkah Kaki**\n\nAnalisis jarak pendaratan kaki terhadap pusat tubuh (*overstride*) dan estimasi ritme langkah (*cadence*).")
        with st.expander("Lihat Panduan Langkah"):
            st.write("Pastikan seluruh bagian kaki hingga pergelangan kaki masuk ke dalam bingkai kamera.")

    with c3:
        st.info("**3. Gerakan Lengan**\n\nPastikan sudut tekukan siku (ideal 65°–110°) dan ayunan tangan kiri-kanan seimbang serta rileks.")
        with st.expander("Lihat Panduan Lengan"):
            st.write("Hindari pakaian yang terlalu longgar di area siku dan bahu agar deteksi titik sendi optimal.")

    st.success("Pindah ke menu **Analisis** di bagian atas untuk mulai mengunggah video lari Anda.")

# =========================================================
# HALAMAN 2: ANALISIS
# =========================================================
elif page == "Analisis":
    st.subheader("UPLOAD VIDEO FILE")
    uploaded_file = st.file_uploader(
        "Pilih video seseorang yang sedang berlari (.MP4, .MKV, .AVI, .MOV)",
        type=["mp4", "mkv", "avi", "mov"]
    )

    if uploaded_file is not None:
        # Simpan file sementara
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(uploaded_file.read())
            input_path = tmp_in.name

        output_path = input_path + "_analyzed.mp4"

        if st.button("Mulai Analisis Form Lari", type="primary"):
            with st.spinner("Mendeteksi pose tubuh dan mengevaluasi aturan biomekanika..."):
                try:
                    analyzer = RunningBiomechanicsAnalyzer(model_path="models/pose_landmarker_full.task")
                    bio_result = analyzer.process_video(input_path, output_video_path=output_path)
                    analyzer.close()

                    kb = RunningFormKnowledgeBase()
                    eval_result = kb.evaluate(bio_result)

                    st.session_state["bio_result"] = bio_result
                    st.session_state["eval_result"] = eval_result
                    st.session_state["output_video"] = output_path
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memproses video: {e}")

    # Tampilkan Hasil Analisis jika tersedia
    if "eval_result" in st.session_state:
        eval_res = st.session_state["eval_result"]
        bio_res = st.session_state["bio_result"]

        if not eval_res.get("success"):
            st.error(eval_res.get("error"))
        else:
            st.divider()
            col_vid, col_res = st.columns([1.1, 1])

            with col_vid:
                st.markdown("### Video Preview")
                out_vid = st.session_state.get("output_video")
                if out_vid and os.path.exists(out_vid):
                    st.video(out_vid)
                st.caption(
                    f"Durasi: {bio_res['duration_sec']} detik | "
                    f"Arah Lari: {bio_res['running_direction']} | "
                    f"Keandalan Deteksi: {int(bio_res['reliability_score'] * 100)}%"
                )

            with col_res:
                st.markdown("### HASIL ANALISIS")
                st.metric("Skor Keseluruhan Form Lari", f"{eval_res['overall_score']} / 100")
                st.write(eval_res["overall_summary"])

                category_labels = {
                    "postur_tubuh": "Postur Tubuh",
                    "langkah_kaki": "Langkah Kaki",
                    "gerakan_lengan": "Gerakan Lengan"
                }

                for key, label in category_labels.items():
                    item = eval_res["categories"].get(key)
                    if item:
                        css_class = f"card-{item['status_level']}"
                        st.markdown(f"""
                        <div class="result-card {css_class}">
                            <div class="card-category">{label}</div>
                            <div class="card-title">{item['title']}</div>
                            <div class="card-advice">{item['advice']}</div>
                            <div class="card-cf">Rule: {item['rule_id']} | Tingkat Keyakinan (CF): {int(item['cf_final'] * 100)}%</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Detail Teknis untuk keperluan pengujian / laporan SBP
            with st.expander("Lihat Detail Parameter Biomekanika & Jejak Inferensi Aturan (KBS)"):
                m = eval_res["raw_metrics"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Kemiringan Badan", f"{m['forward_lean_deg']}°")
                m2.metric("Rasio Overstride", f"{m['overstride_ratio']}")
                m3.metric("Estimasi Cadence", f"{m['cadence_spm']} SPM" if m["cadence_spm"] else "Durasi < 1.5s")
                m4.metric("Rata-rata Sudut Siku", f"{m['avg_elbow_angle_deg']}°")

                st.markdown("**Aturan yang Terpicu (Forward Chaining Trace):**")
                st.table(eval_res["triggered_rules"])