RUNFORMERS - Running Form Detection

1.	SETUP WAJIB PERTAMA KALI (Setelah git clone / git pull PERTAMA KALI)
	Buka terminal di folder utama RUNFORMERS, lalu jalankan:

	- 	Buat venv:
		python -m venv venv

	- 	Aktifkan venv:
		Windows (PowerShell) : .\venv\Scripts\Activate.ps1
		Windows (Git Bash)   : source venv/Scripts/activate
		Mac / Linux          : source venv/bin/activate

	- 	Install library (WAJIB):
		pip install -r requirements.txt

	*Jika PowerShell error saat aktivasi venv, jalankan perintah ini sekali:
	Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

2. 	MENJALANKAN APLIKASI
	Pastikan (venv) aktif di terminal, lalu jalankan:
	streamlit run app.py

3. 	SETELAH GIT PULL BERIKUTNYA
	- Tidak perlu install ulang. Cukup aktifkan venv lalu jalankan: streamlit run app.py
	- Hanya jalankan "pip install -r requirements.txt" jika ada update library baru.		