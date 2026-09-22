import cv2
import mediapipe as mp
import math

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def calculate_angle(a, b, c):
    """
    Menghitung sudut antara tiga titik.
    
    b adalah titik pusat sudut.
    """

    angle = math.degrees(
        math.atan2(c.y - b.y, c.x - b.x)
        -
        math.atan2(a.y - b.y, a.x - b.x)
    )

    angle = abs(angle)

    if angle > 180:
        angle = 360 - angle

    return angle

# =========================================================
# KONFIGURASI
# =========================================================

MODEL_PATH = "models/pose_landmarker_full.task"
VIDEO_PATH = "video/running.mp4"


# =========================================================
# POSE LANDMARKER
# =========================================================

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

detector = vision.PoseLandmarker.create_from_options(options)


# =========================================================
# BUKA VIDEO
# =========================================================

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("ERROR: Video tidak dapat dibuka.")
    exit()


fps = cap.get(cv2.CAP_PROP_FPS)

if fps <= 0:
    fps = 30


frame_number = 0


# =========================================================
# KONEKSI SKELETON
# =========================================================

POSE_CONNECTIONS = [
    
    # Wajah / kepala
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 7),
    (0, 4),
    (4, 5),
    (5, 6),
    (6, 8),

    # Bahu
    (11, 12),

    # Tangan kiri
    (11, 13),
    (13, 15),

    # Tangan kanan
    (12, 14),
    (14, 16),

    # Badan
    (11, 23),
    (12, 24),
    (23, 24),

    # Kaki kiri
    (23, 25),
    (25, 27),

    # Kaki kanan
    (24, 26),
    (26, 28),

    # Kaki bagian bawah
    (27, 29),
    (29, 31),

    (28, 30),
    (30, 32),

    # Sambungan kaki
    (27, 31),
    (28, 32)
]


# =========================================================
# LOOP VIDEO
# =========================================================

while True:

    success, frame = cap.read()

    if not success:
        print("Video selesai.")
        break

    frame_number += 1

    # BGR → RGB
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    # MediaPipe Image
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    # Timestamp
    timestamp_ms = int(
        (frame_number / fps) * 1000
    )

    # Deteksi pose
    result = detector.detect_for_video(
        mp_image,
        timestamp_ms
    )


    # =====================================================
    # GAMBAR SKELETON
    # =====================================================

    if result.pose_landmarks:

        landmarks = result.pose_landmarks[0]

        # Ambil landmark penting

        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]

        left_elbow = landmarks[13]
        right_elbow = landmarks[14]

        left_wrist = landmarks[15]
        right_wrist = landmarks[16]

        left_hip = landmarks[23]
        right_hip = landmarks[24]

        left_knee = landmarks[25]
        right_knee = landmarks[26]

        left_ankle = landmarks[27]
        right_ankle = landmarks[28]

        # AMBIL SUDUT
        left_knee_angle = calculate_angle(
            left_hip,
            left_knee,
            left_ankle
        )

        right_knee_angle = calculate_angle(
            right_hip,
            right_knee,
            right_ankle
        )

        left_elbow_angle = calculate_angle(
            left_shoulder,
            left_elbow,
            left_wrist
        )

        right_elbow_angle = calculate_angle(
            right_shoulder,
            right_elbow,
            right_wrist
        )


        # BUAT TEKS DI VIDEO
        cv2.putText(
            frame,
            f"Left Knee: {left_knee_angle:.1f} deg",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Right Knee: {right_knee_angle:.1f} deg",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Left Elbow: {left_elbow_angle:.1f} deg",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Right Elbow: {right_elbow_angle:.1f} deg",
            (20, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        print(
            "Left Knee:",
            round(left_knee_angle, 2),
            "| Right Knee:",
            round(right_knee_angle, 2)
        )
        print(
            "Left Elbow:",
            round(left_elbow_angle, 2),
            "| Right Elbow:",
            round(right_elbow_angle, 2)
        )


        # -----------------------------------------------
        # GAMBAR GARIS
        # -----------------------------------------------

        for start_idx, end_idx in POSE_CONNECTIONS:

            start = landmarks[start_idx]
            end = landmarks[end_idx]

            start_x = int(
                start.x * frame.shape[1]
            )

            start_y = int(
                start.y * frame.shape[0]
            )

            end_x = int(
                end.x * frame.shape[1]
            )

            end_y = int(
                end.y * frame.shape[0]
            )

            cv2.line(
                frame,
                (start_x, start_y),
                (end_x, end_y),
                (0, 255, 0),
                3
            )


        # -----------------------------------------------
        # GAMBAR TITIK
        # -----------------------------------------------

        for landmark in landmarks:

            x = int(
                landmark.x * frame.shape[1]
            )

            y = int(
                landmark.y * frame.shape[0]
            )

            if (
                0 <= x < frame.shape[1]
                and 0 <= y < frame.shape[0]
            ):

                cv2.circle(
                    frame,
                    (x, y),
                    5,
                    (0, 0, 255),
                    -1
                )


    # =====================================================
    # TAMPILKAN
    # =====================================================

    cv2.imshow(
        "Running Form Detection",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# =========================================================
# CLEAN UP
# =========================================================

cap.release()
cv2.destroyAllWindows()
detector.close()

print("Program selesai.")