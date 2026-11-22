import os
import tempfile
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class RunningBiomechanicsAnalyzer:
    def __init__(self, model_path: str = "models/pose_landmarker_full.task"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model tidak ditemukan di: {model_path}")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    @staticmethod
    def _calculate_angle(a, b, c) -> float:
        """Menghitung sudut (derajat) di titik b dari tiga koordinat (x, y)."""
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba = a - b
        bc = c - b
        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    @staticmethod
    def _calculate_trunk_lean(hip, shoulder, dir_sign: float = 1.0) -> float:
        """Kemiringan badan (derajat) terhadap vertikal.
        Positif = condong ke depan (searah lari), negatif = condong ke belakang."""
        dx = (shoulder[0] - hip[0]) * dir_sign
        dy = abs(hip[1] - shoulder[1]) + 1e-6
        return float(np.degrees(np.arctan2(dx, dy)))

    def _create_browser_video_writer(self, width: int, height: int, fps: float):
        """Membuat VideoWriter dengan codec H.264/WebM agar bisa diputar di browser Streamlit."""
        tmp_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        writer = cv2.VideoWriter(tmp_mp4, cv2.VideoWriter_fourcc(*"avc1"), fps, (width, height))
        if writer.isOpened():
            return writer, tmp_mp4

        os.remove(tmp_mp4)
        tmp_webm = tempfile.NamedTemporaryFile(delete=False, suffix=".webm").name
        writer = cv2.VideoWriter(tmp_webm, cv2.VideoWriter_fourcc(*"vp80"), fps, (width, height))
        return writer, tmp_webm

    @staticmethod
    def _extract_landing_records(leg_records: list) -> list:
        """Mengembalikan catatan frame saat kaki menyentuh tanah (initial contact)."""
        if len(leg_records) < 3:
            return []

        drops = np.array([r["drop"] for r in leg_records])
        min_contact_drop = np.percentile(drops, 70)
        landing = []

        for i in range(1, len(leg_records) - 1):
            curr = leg_records[i]
            is_local_bottom = curr["drop"] >= leg_records[i - 1]["drop"] and curr["drop"] >= leg_records[i + 1]["drop"]
            is_ground_level = curr["drop"] >= min_contact_drop
            is_front_landing = curr["ankle_ahead_of_hip"] >= -0.04 * curr["leg_length"]

            if is_local_bottom and is_ground_level and is_front_landing:
                landing.append(curr)

        # Fallback untuk klip sangat pendek
        if not landing:
            landing = [r for r in leg_records
                       if r["drop"] >= min_contact_drop and r["ankle_ahead_of_hip"] >= 0]

        return landing

    def process_video(self, input_video_path: str):
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            raise ValueError("Gagal membuka file video.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out, output_video_path = self._create_browser_video_writer(width, height, fps)

        trunk_angles = []
        elbow_angles = []
        left_leg_records = []
        right_leg_records = []

        cyan_bones = [(11, 23), (12, 24), (23, 25), (25, 27), (12, 14), (14, 16)]
        amber_bones = [(24, 26), (26, 28), (11, 13), (13, 15)]
        joint_indices = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_idx * 1000) / fps)
            frame_idx += 1

            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks:
                lm = result.pose_landmarks[0]
                pts = {i: (int(lm[i].x * width), int(lm[i].y * height)) for i in range(33)}

                # Tentukan arah hadap lari (+1 = ke kanan, -1 = ke kiri) dari posisi ujung kaki vs tumit
                toe_vs_heel = ((lm[31].x - lm[29].x) + (lm[32].x - lm[30].x)) / 2.0
                if abs(toe_vs_heel) > 0.01:
                    dir_sign = 1.0 if toe_vs_heel > 0 else -1.0
                else:
                    mid_hip_x = (lm[23].x + lm[24].x) / 2.0
                    dir_sign = 1.0 if lm[0].x >= mid_hip_x else -1.0

                # Pilih sisi dominan untuk postur tubuh & ayunan lengan
                left_vis = lm[11].visibility + lm[23].visibility + lm[25].visibility
                right_vis = lm[12].visibility + lm[24].visibility + lm[26].visibility

                if right_vis >= left_vis:
                    shoulder, elbow, wrist = pts[12], pts[14], pts[16]
                    hip = pts[24]
                else:
                    shoulder, elbow, wrist = pts[11], pts[13], pts[15]
                    hip = pts[23]

                trunk_angles.append(self._calculate_trunk_lean(hip, shoulder, dir_sign))
                elbow_angles.append(self._calculate_angle(shoulder, elbow, wrist))

                # Rekam data pergerakan kaki kiri (23, 25, 27) & kanan (24, 26, 28)
                for h_idx, k_idx, a_idx, target_list in [
                    (23, 25, 27, left_leg_records),
                    (24, 26, 28, right_leg_records),
                ]:
                    if lm[h_idx].visibility > 0.45 and lm[k_idx].visibility > 0.45 and lm[a_idx].visibility > 0.45:
                        h_pt, k_pt, a_pt = pts[h_idx], pts[k_idx], pts[a_idx]
                        leg_len = float(np.linalg.norm(np.array(h_pt) - np.array(a_pt))) + 1e-6

                        # Jarak maju pergelangan kaki di depan lutut (0 jika di belakang lutut)
                        shin_forward_dx = max(0.0, (a_pt[0] - k_pt[0]) * dir_sign)
                        shin_dy = max(1.0, float(a_pt[1] - k_pt[1]))
                        shin_angle = float(np.degrees(np.arctan2(shin_forward_dx, shin_dy)))

                        # Metrik baru: posisi seluruh kaki relatif terhadap pinggul
                        ankle_ahead = float((a_pt[0] - h_pt[0]) * dir_sign)
                        leg_dy = max(1.0, float(a_pt[1] - h_pt[1]))
                        leg_angle = float(np.degrees(np.arctan2(ankle_ahead, leg_dy)))
                        knee_angle = self._calculate_angle(h_pt, k_pt, a_pt)

                        target_list.append({
                            "drop": float(a_pt[1] - h_pt[1]),
                            "ankle_ahead_of_hip": ankle_ahead,
                            "leg_length": leg_len,
                            "shin_angle": shin_angle,
                            "leg_angle": leg_angle,
                            "ahead_ratio": ankle_ahead / leg_len,
                            "knee_angle": knee_angle,
                        })

                # Gambar kerangka pose pada frame
                for p1, p2 in cyan_bones:
                    cv2.line(frame, pts[p1], pts[p2], (190, 215, 55), 3, lineType=cv2.LINE_AA)
                for p1, p2 in amber_bones:
                    cv2.line(frame, pts[p1], pts[p2], (50, 200, 255), 3, lineType=cv2.LINE_AA)
                for idx in joint_indices:
                    cv2.circle(frame, pts[idx], 5, (40, 190, 255), -1, lineType=cv2.LINE_AA)

            out.write(frame)

        cap.release()
        out.release()
        self.landmarker.close()

        if not trunk_angles:
            raise ValueError("Pose pelari tidak terdeteksi dalam video. Pastikan seluruh tubuh terlihat jelas dari samping.")

        landing = (
            self._extract_landing_records(left_leg_records)
            + self._extract_landing_records(right_leg_records)
        )
        if not landing:
            raise ValueError(
                "Momen pendaratan kaki tidak terdeteksi. Pastikan video tampak samping, "
                "seluruh tubuh terlihat, dan ada beberapa langkah."
            )

        def _avg(key: str) -> float:
            return float(np.mean([r[key] for r in landing]))

        metrics = {
            "avg_trunk_lean": float(np.mean(trunk_angles)),
            "landing_shin_angle": _avg("shin_angle"),
            "landing_leg_angle": _avg("leg_angle"),
            "landing_ankle_ahead": _avg("ahead_ratio"),
            "landing_knee_angle": _avg("knee_angle"),
            "avg_elbow_angle": float(np.mean(elbow_angles)),
        }
        return metrics, output_video_path