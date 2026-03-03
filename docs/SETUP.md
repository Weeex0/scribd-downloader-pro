# Detailed Setup Guide

This guide walks you through everything step by step, even if you've never used Python or the terminal before.

---

## Windows Setup

### 1. Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow **"Download Python 3.x.x"** button
3. Run the installer
4. ⚠️ **Important:** Check the box that says **"Add Python to PATH"** before clicking Install

### 2. Open CMD

Press `Windows + R`, type `cmd`, press Enter.

### 3. Navigate to the project folder

If you saved this project to your Desktop:
```cmd
cd C:\Users\YourName\Desktop\scribd-downloader-pro
```
Replace `YourName` with your actual Windows username.

### 4. Install dependencies

```cmd
pip install playwright pymupdf pillow requests beautifulsoup4
playwright install chromium
```

The second command downloads a small browser (~150MB). This only happens once.

### 5. Run the script

```cmd
python src/scribd_downloader.py https://www.scribd.com/document/XXXXXX/Title --cookies cookies.json
```

---

## Mac / Linux Setup

```bash
# Install dependencies
pip3 install playwright pymupdf pillow requests beautifulsoup4
playwright install chromium

# Run
python3 src/scribd_downloader.py https://www.scribd.com/document/XXXXXX/Title --cookies cookies.json
```

---

## Getting your cookies.json

Cookies are what tell the Scribd website "this is a logged-in user". Without them the script can only access publicly visible documents.

1. Install **Cookie-Editor** in your browser:
   - [Chrome / Edge / Brave](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - [Firefox](https://addons.mozilla.org/firefox/addon/cookie-editor/)

2. Go to **scribd.com** and log in normally

3. Click the Cookie-Editor icon in the browser toolbar (top right)

4. Click **"Export All"** — this copies all cookies to your clipboard

5. Open Notepad (Windows) or TextEdit (Mac), paste, and save as `cookies.json`  
   Put this file in the same folder as the script, or provide its full path with `--cookies`

> 🔒 **Keep cookies.json private!** It contains your login session. Never upload it to GitHub — the `.gitignore` file already prevents this.

---

## Where is my PDF?

After the script finishes, look for a folder called `scribd_output` in whichever directory you ran the command from.

```
scribd_output/
├── Document_Title.pdf    ← your PDF is here
└── images/
    ├── p0001.jpg
    ├── p0002.jpg
    └── ...
```
