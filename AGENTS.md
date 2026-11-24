# AGENTS.md

## What this is
A Streamlit app (Indonesian UI) that scores running form from a side-view video. MediaPipe PoseLandmarker extracts joint landmarks, OpenCV draws the skeleton and writes an annotated video, and rule-based certainty factors in `knowledge_base.py` grade posture, foot strike, and arm swing.

## Setup & run
- The requirements file is misspelled: install with `pip install -r requirments.txt`. There is no `requirements.txt` despite what `readme.txt` says.
- Run from the repo root only: `streamlit run app.py`. All resource paths (`assets/style.css`, `assets/icons/*`, `models/pose_landmarker_full.task`) are CWD-relative.
- Activate the existing venv with `.\venv\Scripts\Activate.ps1` (PowerShell). Python 3.13 is used.
- No tests, linter, typechecker, or CI exist. Verify changes by running the app or the headless smoke test below.
- Smoke test (uses the only committed video fixture, `video/running.mp4`; takes tens of seconds):
  ```powershell
  .\venv\Scripts\python.exe -c "from biomechanics import RunningBiomechanicsAnalyzer; from knowledge_base import evaluate_running_form; m,p=RunningBiomechanicsAnalyzer().process_video('video/running.mp4'); print(m); print(p); print(evaluate_running_form(m))"
  ```

## Code map
- `app.py` — entire UI. "Pages" are just `st.session_state.page` values (`Beranda` / `Analisis`); there is no `pages/` directory. Styling comes from `assets/style.css`, injected once per run; theme is `.streamlit/config.toml`.
- `biomechanics.py` — `RunningBiomechanicsAnalyzer.process_video()` returns `(metrics: dict, annotated_video_path: str)`. Metrics keys are consumed by `knowledge_base.evaluate_running_form()`; keep the names in sync.
- `knowledge_base.py` — all clinical thresholds and CF logic. Returns `{"postur", "langkah", "lengan"}`, each with `level` ∈ `ideal|warning|danger|neutral`, `status`, `advice`. The UI uses `level` directly as CSS class/badge suffix, so new levels need matching `.card-*` / `.badge-*` rules in `assets/style.css`.
- `models/pose_landmarker_full.task` (~9.4 MB) is committed and required; don't regenerate or delete it.
- `video/running.mp4` is a tracked sample, not referenced by the app.

## Gotchas
- `RunningBiomechanicsAnalyzer` closes the MediaPipe landmarker at the end of `process_video()`. Create a fresh instance for each analysis; a second `process_video()` call on the same instance will fail.
- Analysis is synchronous inside a Streamlit rerun. On any exception, `app.py` still switches to the Analisis page and reruns, which discards the `st.error` message — debug analysis failures headlessly, not through the UI.
- Uploaded input copies and annotated output videos go to the system temp dir and are never cleaned up (~20+ MB per run).
- Metrics assume a side-view clip with the full body visible. Facing direction is inferred per frame from toe-vs-heel landmark x positions; the threshold constants are tuned for this camera setup.
- `get_icon_uri()` accepts either a CWD-relative path or a bare icon name resolved under `assets/icons/` as `.svg`, `.png`, or `.webp`.
- The custom CSS depends on Streamlit internals (`data-testid` attributes and `.st-key-*` button keys). Preserve widget `key`s (`nav_beranda`, `nav_analisis`) when editing navigation.
- UI copy is Indonesian; keep new user-facing text consistent with it.
