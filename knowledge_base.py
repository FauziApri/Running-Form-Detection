from dataclasses import dataclass
from typing import Callable, Dict, Any, List


@dataclass
class KnowledgeRule:
    rule_id: str
    category: str          # 'postur_tubuh', 'langkah_kaki', 'gerakan_lengan'
    status_level: str      # 'good', 'warning', 'danger'
    title: str
    advice: str
    cf_expert: float       # Bobot keyakinan pakar (0.0 - 1.0)
    condition_text: str
    condition_fn: Callable[[Dict[str, Any]], bool]


class RunningFormKnowledgeBase:
    """
    Sistem Berbasis Pengetahuan (Knowledge-Based System) menggunakan Forward Chaining
    dan Certainty Factor untuk mengevaluasi teknik lari.
    """

    def __init__(self):
        self.rules: List[KnowledgeRule] = [
            # =========================================================
            # DOMAIN 1: POSTUR TUBUH (FORWARD LEAN)
            # =========================================================
            KnowledgeRule(
                rule_id="R01",
                category="postur_tubuh",
                status_level="good",
                title="Sudah Bagus (Condong ideal)",
                advice="Pertahankan posisi badan yang sedikit condong ke depan dari pergelangan kaki.",
                cf_expert=0.92,
                condition_text="IF 5.0 <= forward_lean_deg <= 15.0",
                condition_fn=lambda f: 5.0 <= f["forward_lean_deg"] <= 15.0
            ),
            KnowledgeRule(
                rule_id="R02",
                category="postur_tubuh",
                status_level="warning",
                title="Terlalu Tegak / Kaku",
                advice="Condongkan tubuh sedikit ke depan (sekitar 5-15 derajat) dari pergelangan kaki untuk membantu momentum lari.",
                cf_expert=0.85,
                condition_text="IF forward_lean_deg < 5.0",
                condition_fn=lambda f: f["forward_lean_deg"] < 5.0
            ),
            KnowledgeRule(
                rule_id="R03",
                category="postur_tubuh",
                status_level="danger",
                title="Terlalu Membungkuk / Condong",
                advice="Tegakkan dada, arahkan pandangan lurus ke depan, dan aktifkan otot perut (core) agar pinggul tidak tertekuk.",
                cf_expert=0.90,
                condition_text="IF forward_lean_deg > 15.0",
                condition_fn=lambda f: f["forward_lean_deg"] > 15.0
            ),

            # =========================================================
            # DOMAIN 2: LANGKAH KAKI (OVERSTRIDE & CADENCE)
            # =========================================================
            KnowledgeRule(
                rule_id="R04",
                category="langkah_kaki",
                status_level="danger",
                title="Terlalu jauh (overstride)",
                advice="Pendekkan langkah kaki agar pendaratan lebih dekat ke bawah pusat tubuh dan tingkatkan ritme langkah.",
                cf_expert=0.90,
                condition_text="IF overstride_ratio > 0.30 OR (overstride_ratio > 0.26 AND knee_angle_at_strike_deg > 168)",
                condition_fn=lambda f: (
                    f["overstride_ratio"] > 0.30
                    or (f["overstride_ratio"] > 0.26 and f["knee_angle_at_strike_deg"] > 168.0)
                )
            ),
            KnowledgeRule(
                rule_id="R05",
                category="langkah_kaki",
                status_level="warning",
                title="Ritme Langkah Rendah (Cadence Lambat)",
                advice="Tingkatkan frekuensi langkah mendekati 160-180 langkah/menit dengan ayunan kaki yang lebih ringan.",
                cf_expert=0.82,
                condition_text="IF overstride_ratio <= 0.30 AND cadence_spm IS NOT None AND cadence_spm < 155",
                condition_fn=lambda f: (
                    f["overstride_ratio"] <= 0.30
                    and f["cadence_spm"] is not None
                    and f["cadence_spm"] < 155.0
                )
            ),
            KnowledgeRule(
                rule_id="R06",
                category="langkah_kaki",
                status_level="good",
                title="Langkah Efisien & Proporsional",
                advice="Pendaratan kaki sudah berada dekat di bawah titik berat tubuh. Pertahankan ritme langkah Anda.",
                cf_expert=0.88,
                condition_text="IF overstride_ratio <= 0.30 AND (cadence_spm IS None OR cadence_spm >= 155)",
                condition_fn=lambda f: (
                    f["overstride_ratio"] <= 0.30
                    and (f["cadence_spm"] is None or f["cadence_spm"] >= 155.0)
                )
            ),

            # =========================================================
            # DOMAIN 3: GERAKAN LENGAN (ELBOW ANGLE & SYMMETRY)
            # =========================================================
            KnowledgeRule(
                rule_id="R07",
                category="gerakan_lengan",
                status_level="warning",
                title="Sedikit lebar",
                advice="Rilekskan bahu dan tarik siku lebih ke belakang dengan tekukan sekitar 80-100 derajat.",
                cf_expert=0.86,
                condition_text="IF avg_elbow_angle_deg > 110.0",
                condition_fn=lambda f: f["avg_elbow_angle_deg"] > 110.0
            ),
            KnowledgeRule(
                rule_id="R08",
                category="gerakan_lengan",
                status_level="warning",
                title="Tekukan Siku Terlalu Rapat",
                advice="Turunkan bahu agar tidak tegang dan longgarkan sedikit sudut siku ke kisaran 80-100 derajat.",
                cf_expert=0.84,
                condition_text="IF avg_elbow_angle_deg < 65.0",
                condition_fn=lambda f: f["avg_elbow_angle_deg"] < 65.0
            ),
            KnowledgeRule(
                rule_id="R09",
                category="gerakan_lengan",
                status_level="warning",
                title="Ayunan Lengan Kurang Simetris",
                advice="Seimbangkan ayunan lengan kiri dan kanan dari sendi bahu tanpa menyilang garis tengah tubuh.",
                cf_expert=0.80,
                condition_text="IF 65.0 <= avg_elbow_angle_deg <= 110.0 AND elbow_asymmetry_deg > 18.0",
                condition_fn=lambda f: (
                    65.0 <= f["avg_elbow_angle_deg"] <= 110.0
                    and f["elbow_asymmetry_deg"] > 18.0
                )
            ),
            KnowledgeRule(
                rule_id="R10",
                category="gerakan_lengan",
                status_level="good",
                title="Ayunan Lengan Seimbang & Rileks",
                advice="Sudut siku dan keseimbangan ayunan tangan sudah ideal untuk menjaga stabilitas tubuh.",
                cf_expert=0.90,
                condition_text="IF 65.0 <= avg_elbow_angle_deg <= 110.0 AND elbow_asymmetry_deg <= 18.0",
                condition_fn=lambda f: (
                    65.0 <= f["avg_elbow_angle_deg"] <= 110.0
                    and f["elbow_asymmetry_deg"] <= 18.0
                )
            ),
        ]

    def evaluate(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Menjalankan mesin inferensi (Forward Chaining) terhadap fakta hasil ekstraksi video."""
        if not analysis_result.get("success"):
            return {"success": False, "error": analysis_result.get("error", "Analisis gagal.")}

        facts = analysis_result["metrics"]
        cf_evidence = analysis_result["reliability_score"]

        evaluated_categories = {}
        triggered_rules = []

        for rule in self.rules:
            if rule.category in evaluated_categories:
                continue

            if rule.condition_fn(facts):
                cf_final = round(rule.cf_expert * cf_evidence, 2)
                evaluated_categories[rule.category] = {
                    "rule_id": rule.rule_id,
                    "status_level": rule.status_level,
                    "title": rule.title,
                    "advice": rule.advice,
                    "cf_expert": rule.cf_expert,
                    "cf_evidence": cf_evidence,
                    "cf_final": cf_final
                }
                triggered_rules.append({
                    "Rule ID": rule.rule_id,
                    "Kategori": rule.category.replace("_", " ").title(),
                    "Kondisi Terpenuhi": rule.condition_text,
                    "Hasil": rule.title,
                    "CF Akhir": f"{cf_final * 100:.0f}%"
                })

        # Penilaian Keseluruhan (Overall Score)
        score_map = {"good": 100, "warning": 65, "danger": 35}
        scores = [score_map[v["status_level"]] for v in evaluated_categories.values()]
        overall_score = round(sum(scores) / len(scores)) if scores else 0

        if overall_score >= 85:
            overall_summary = "Form lari secara keseluruhan sudah sangat baik dan efisien."
        elif overall_score >= 60:
            overall_summary = "Form lari cukup baik, namun ada beberapa indikator teknis yang perlu disesuaikan."
        else:
            overall_summary = "Ditemukan beberapa penyimpangan postur yang berisiko menurunkan efisiensi dan memicu cedera."

        return {
            "success": True,
            "overall_score": overall_score,
            "overall_summary": overall_summary,
            "reliability_score": cf_evidence,
            "categories": evaluated_categories,
            "triggered_rules": triggered_rules,
            "raw_metrics": facts
        }