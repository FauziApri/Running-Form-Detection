def cf_combine(cf1: float, cf2: float) -> float:
    """Menggabungkan dua nilai Certainty Factor dengan tanda yang sama."""
    return cf1 + cf2 * (1.0 - cf1)

def _evaluasi_langkah(metrics: dict) -> dict:
    shin = metrics["landing_shin_angle"]
    leg = metrics.get("landing_leg_angle")      # pinggul -> pergelangan vs vertikal
    ahead = metrics.get("landing_ankle_ahead")  # jarak ankle di depan pinggul / panjang kaki
    knee = metrics.get("landing_knee_angle")    # sudut lutut saat kontak

    evidence = []
    if shin > 16.0:
        evidence.append(("tulang kering miring ke depan", 0.55))
    elif shin > 11.0:
        evidence.append(("tulang kering agak miring", 0.35))
    if leg is not None and leg > 16.0:
        evidence.append(("kaki jauh di depan pinggul", 0.60))
    if ahead is not None and ahead > 0.28:
        evidence.append(("pendaratan di depan pusat massa", 0.60))
    if knee is not None and leg is not None and knee > 160.0 and leg > 11.0:
        evidence.append(("lutut hampir lurus saat mendarat", 0.50))

    if not evidence:
        # keyakinan "bagus" lebih rendah jika hanya shin yang tersedia
        cf = 0.85 if leg is not None and ahead is not None else 0.70
        return {
            "level": "ideal",
            "status": f"Sudah Bagus (CF: {int(cf * 100)}%)",
            "advice": f"Pendaratan kaki sejajar di bawah tubuh (sudut tulang kering {shin:.1f}°)",
            "cf": cf,
        }

    cf = 0.0
    for _, c in evidence:
        cf = cf_combine(cf, c)
    cf = min(cf, 0.95)

    if len(evidence) >= 2:
        level, label = "danger", "Terlalu jauh / overstride"
        advice = "Pendekkan langkah kaki agar mendarat lebih dekat ke bawah tubuh"
    else:
        level, label = "warning", "Langkah sedikit melebar"
        advice = "Tingkatkan frekuensi langkah agar pendaratan lebih dekat ke bawah pinggul"

    return {
        "level": level,
        "status": f"{label} (CF: {int(cf * 100)}%)",
        "advice": f"{advice} ({', '.join(n for n, _ in evidence)})",
        "cf": cf,
    }

def evaluate_running_form(metrics: dict) -> dict:
    trunk = metrics["avg_trunk_lean"]
    shin_angle = metrics["landing_shin_angle"]
    elbow = metrics["avg_elbow_angle"]

    # --- 1. EVALUASI POSTUR TUBUH ---
    if 5.0 <= trunk <= 16.0:
        cf_postur = 0.90
        postur_result = {
            "level": "ideal",
            "status": f"Sudah Bagus (CF: {int(cf_postur * 100)}%)",
            "advice": f"Condong ideal ({trunk:.1f}° ke depan)",
        }
    elif trunk < 5.0:
        cf_postur = 0.72
        postur_result = {
            "level": "warning",
            "status": f"Terlalu tegak (CF: {int(cf_postur * 100)}%)",
            "advice": f"Condongkan badan sedikit ke depan dari pergelangan kaki ({trunk:.1f}°)",
        }
    else:
        cf_postur = min(0.95, 0.70 + (trunk - 16.0) * 0.02)
        postur_result = {
            "level": "danger",
            "status": f"Terlalu membungkuk (CF: {int(cf_postur * 100)}%)",
            "advice": f"Tegakkan dada dan pandangan ke depan ({trunk:.1f}°)",
        }

    # --- 2. EVALUASI LANGKAH KAKI (BERDASARKAN SUDUT PENDARATAN / INITIAL CONTACT) ---
    langkah_result = _evaluasi_langkah(metrics)
    cf_langkah = langkah_result.pop("cf")
    
    # --- 3. EVALUASI GERAKAN LENGAN ---
    if 70.0 <= elbow <= 105.0:
        cf_lengan = 0.90
        lengan_result = {
            "level": "ideal",
            "status": f"Sudah Bagus (CF: {int(cf_lengan * 100)}%)",
            "advice": f"Sudut ayunan siku kompak dan seimbang ({elbow:.1f}°)",
        }
    elif (55.0 <= elbow < 70.0) or (105.0 < elbow <= 122.0):
        cf_lengan = 0.78
        ket = "Sedikit lebar" if elbow > 105.0 else "Sedikit terlalu menekuk"
        lengan_result = {
            "level": "warning",
            "status": f"{ket} (CF: {int(cf_lengan * 100)}%)",
            "advice": f"Rilekskan bahu dan jaga sudut siku sekitar 90° ({elbow:.1f}°)",
        }
    else:
        cf_lengan = 0.88
        lengan_result = {
            "level": "danger",
            "status": f"Ayunan lengan kurang efisien (CF: {int(cf_lengan * 100)}%)",
            "advice": f"Tarik siku lebih ke belakang dengan sudut mendekati 90° ({elbow:.1f}°)",
        }

    return {
        "postur": postur_result,
        "langkah": langkah_result,
        "lengan": lengan_result,
    }