import math
import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
    (27, 29), (29, 31),
    (28, 30), (30, 32),
    (27, 31), (28, 32)
]


def calculate_angle_2d(a, b, c, width: int, height: int) -> float:
    """Menghitung sudut 2D (dalam derajat) pada titik pusat b dalam skala piksel."""
    ax, ay = a.x * width, a.y * height
    bx, by = b.x * width, b.y * height
    cx, cy = c.x * width, c.y * height

    angle = math.degrees(
        math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx)
    )
    angle = abs(angle)
    return 360.0 - angle if angle > 180.0 else angle


def euclidean_distance_2d(a, b, width: int, height: int) -> float:
    """Menghitung jarak Euclidean dalam piksel antara dua landmark."""
    dx = (a.x - b.x) * width
    dy = (a.y - b.y) * height
    return math.hypot(dx, dy)


def detect_running_direction(landmarks) -> int:
    """
    Mendeteksi arah hadap pelari dari tampak samping:
    +1 jika berlari ke arah KANAN layar, -1 jika berlari ke arah KIRI layar.
    """
    nose = landmarks[0]
    mid_shoulder_x = (landmarks[11].x + landmarks[12].x) / 2.0
    foot_diff = (landmarks[31].x - landmarks[29].x) + (landmarks[32].x - landmarks[30].x)

    score = (nose.x - mid_shoulder_x) + foot_diff
    return 1 if score >= 0 else -1


def detect_foot_strikes(y_series: list, min_distance: int, min_prominence: float) -> list:
    """
    Mendeteksi indeks frame saat kaki menyentuh tanah (puncak lokal koordinat Y).
    Koordinat Y membesar ke arah bawah layar.
    """
    n = len(y_series)
    if n < 3:
        return [y_series.index(max(y_series))] if n > 0 else []

    peaks = []
    for i in range(1, n - 1):
        if y_series[i] >= y_series[i - 1] and y_series[i] > y_series[i + 1]:
            left_bound = max(0, i - min_distance)
            right_bound = min(n, i + min_distance + 1)
            local_min = min(y_series[left_bound:right_bound])

            if (y_series[i] - local_min) >= min_prominence:
                if not peaks or (i - peaks[-1]) >= min_distance:
                    peaks.append(i)
                elif y_series[i] > y_series[peaks[-1]]:
                    peaks[-1] = i

    if not peaks:
        peaks.append(y_series.index(max(y_series)))
    return peaks


class RunningBiomechanicsAnalyzer:
    def __init__(self, model_path: str = "models/pose_landmarker_full.task"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model MediaPipe tidak ditemukan di: {model_path}")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def _create_video_writer(self, output_path: str, fps: float, width: int, height: int):
        """Mencoba codec yang kompatibel dengan browser web (H.264 / VP8) lalu fallback ke mp4v."""
        for codec in ["avc1", "vp80", "mp4v"]:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer
        return None

    def process_video(self, video_path: str, output_video_path: str = None) -> dict:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Video tidak dapat dibuka atau format tidak didukung.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or math.isnan(fps):
            fps = 30.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        writer = None
        if output_video_path:
            writer = self._create_video_writer(output_video_path, fps, width, height)

        # Penampung data deret waktu (temporal tracking)
        lean_angles = []
        left_elbow_angles = []
        right_elbow_angles = []
        left_knee_angles = []
        right_knee_angles = []
        left_ankle_y = []
        right_ankle_y = []
        left_overstride_ratios = []
        right_overstride_ratios = []
        leg_lengths = []
        directions = []
        visibility_scores = []

        frame_idx = 0
        detected_frames = 0
        last_timestamp_ms = -1

        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break

                frame_idx += 1
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                timestamp_ms = int((frame_idx / fps) * 1000)
                if timestamp_ms <= last_timestamp_ms:
                    timestamp_ms = last_timestamp_ms + 1
                last_timestamp_ms = timestamp_ms

                result = self.detector.detect_for_video(mp_image, timestamp_ms)

                if result.pose_landmarks:
                    detected_frames += 1
                    lm = result.pose_landmarks[0]

                    direction = detect_running_direction(lm)
                    directions.append(direction)

                    # 1. Hitung Kemiringan Badan (Forward Lean)
                    hip_mid_x = ((lm[23].x + lm[24].x) / 2.0) * width
                    hip_mid_y = ((lm[23].y + lm[24].y) / 2.0) * height
                    sh_mid_x = ((lm[11].x + lm[12].x) / 2.0) * width
                    sh_mid_y = ((lm[11].y + lm[12].y) / 2.0) * height

                    dx_torso = (sh_mid_x - hip_mid_x) * direction
                    dy_torso = hip_mid_y - sh_mid_y  # Positif ke arah atas
                    if dy_torso > 1e-5:
                        lean_deg = math.degrees(math.atan2(dx_torso, dy_torso))
                        lean_angles.append(lean_deg)

                    # 2. Hitung Sudut Siku (Gerakan Lengan)
                    l_elbow = calculate_angle_2d(lm[11], lm[13], lm[15], width, height)
                    r_elbow = calculate_angle_2d(lm[12], lm[14], lm[16], width, height)
                    left_elbow_angles.append(l_elbow)
                    right_elbow_angles.append(r_elbow)

                    # 3. Hitung Sudut Lutut & Posisi Langkah Kaki
                    l_knee = calculate_angle_2d(lm[23], lm[25], lm[27], width, height)
                    r_knee = calculate_angle_2d(lm[24], lm[26], lm[28], width, height)
                    left_knee_angles.append(l_knee)
                    right_knee_angles.append(r_knee)

                    l_leg_len = (
                        euclidean_distance_2d(lm[23], lm[25], width, height)
                        + euclidean_distance_2d(lm[25], lm[27], width, height)
                    )
                    r_leg_len = (
                        euclidean_distance_2d(lm[24], lm[26], width, height)
                        + euclidean_distance_2d(lm[26], lm[28], width, height)
                    )
                    avg_leg_len = max((l_leg_len + r_leg_len) / 2.0, 1.0)
                    leg_lengths.append(avg_leg_len)

                    # Jarak horizontal pergelangan kaki di depan pinggul (ternormalisasi panjang kaki)
                    l_reach = ((lm[27].x - lm[23].x) * width * direction) / max(l_leg_len, 1.0)
                    r_reach = ((lm[28].x - lm[24].x) * width * direction) / max(r_leg_len, 1.0)

                    left_ankle_y.append(lm[27].y * height)
                    right_ankle_y.append(lm[28].y * height)
                    left_overstride_ratios.append(l_reach)
                    right_overstride_ratios.append(r_reach)

                    # Skor keandalan (rata-rata visibilitas titik tubuh utama)
                    key_indices = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
                    frame_vis = sum(lm[i].visibility for i in key_indices) / len(key_indices)
                    visibility_scores.append(frame_vis)

                    # Gambar skeleton pada video output
                    if writer:
                        self._draw_overlay(
                            frame, lm, width, height,
                            lean_angles[-1] if lean_angles else 0.0,
                            (l_elbow + r_elbow) / 2.0,
                            (l_knee + r_knee) / 2.0
                        )

                if writer:
                    writer.write(frame)

        finally:
            cap.release()
            if writer:
                writer.release()

        if detected_frames < 5:
            return {
                "success": False,
                "error": "Tubuh pelari tidak terdeteksi dengan jelas pada video. Pastikan seluruh tubuh terlihat dari samping."
            }

        # Agregasi metrik seluruh video
        duration_sec = frame_idx / fps
        avg_leg_px = sum(leg_lengths) / len(leg_lengths)
        min_step_frames = max(int(0.32 * fps), 3)
        min_step_lift = 0.06 * avg_leg_px

        l_strikes = detect_foot_strikes(left_ankle_y, min_step_frames, min_step_lift)
        r_strikes = detect_foot_strikes(right_ankle_y, min_step_frames, min_step_lift)

        # Evaluasi overstriding tepat pada frame foot-strike
        strike_reaches = (
            [left_overstride_ratios[i] for i in l_strikes]
            + [right_overstride_ratios[i] for i in r_strikes]
        )
        strike_knees = (
            [left_knee_angles[i] for i in l_strikes]
            + [right_knee_angles[i] for i in r_strikes]
        )

        avg_overstride_ratio = sum(strike_reaches) / len(strike_reaches)
        avg_knee_at_strike = sum(strike_knees) / len(strike_knees)

        # Estimasi cadence (langkah per menit)
        total_steps = len(l_strikes) + len(r_strikes)
        cadence_spm = (total_steps / duration_sec) * 60.0 if duration_sec >= 1.5 else None

        avg_lean = sum(lean_angles) / len(lean_angles) if lean_angles else 0.0
        avg_l_elbow = sum(left_elbow_angles) / len(left_elbow_angles)
        avg_r_elbow = sum(right_elbow_angles) / len(right_elbow_angles)
        avg_elbow = (avg_l_elbow + avg_r_elbow) / 2.0
        elbow_asymmetry = abs(avg_l_elbow - avg_r_elbow)

        detection_ratio = detected_frames / max(frame_idx, 1)
        mean_visibility = sum(visibility_scores) / len(visibility_scores)
        reliability = round(min(1.0, detection_ratio * mean_visibility), 2)

        return {
            "success": True,
            "duration_sec": round(duration_sec, 2),
            "total_frames": frame_idx,
            "detected_frames": detected_frames,
            "running_direction": "Kanan" if sum(directions) >= 0 else "Kiri",
            "reliability_score": reliability,
            "metrics": {
                "forward_lean_deg": round(avg_lean, 1),
                "overstride_ratio": round(avg_overstride_ratio, 3),
                "knee_angle_at_strike_deg": round(avg_knee_at_strike, 1),
                "cadence_spm": round(cadence_spm, 1) if cadence_spm else None,
                "avg_elbow_angle_deg": round(avg_elbow, 1),
                "left_elbow_deg": round(avg_l_elbow, 1),
                "right_elbow_deg": round(avg_r_elbow, 1),
                "elbow_asymmetry_deg": round(elbow_asymmetry, 1),
            }
        }

    def _draw_overlay(self, frame, lm, w: int, h: int, lean: float, elbow: float, knee: float):
        for start_idx, end_idx in POSE_CONNECTIONS:
            s, e = lm[start_idx], lm[end_idx]
            if s.visibility > 0.5 and e.visibility > 0.5:
                pt1 = (int(s.x * w), int(s.y * h))
                pt2 = (int(e.x * w), int(e.y * h))
                cv2.line(frame, pt1, pt2, (46, 204, 113), 3)

        for point in lm:
            if point.visibility > 0.5:
                cx, cy = int(point.x * w), int(point.y * h)
                if 0 <= cx < w and 0 <= cy < h:
                    cv2.circle(frame, (cx, cy), 5, (52, 152, 219), -1)

        # Panel info ringkas di sudut kiri atas video
        cv2.rectangle(frame, (12, 12), (295, 112), (20, 25, 35), -1)
        cv2.putText(frame, f"Condong Badan : {lean:.1f} deg", (22, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Sudut Siku    : {elbow:.1f} deg", (22, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Sudut Lutut   : {knee:.1f} deg", (22, 98),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def close(self):
        self.detector.close()