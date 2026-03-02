<div align="center">

# 📄 Scribd Downloader PRO

**Download any Scribd document as a clean, high-quality PDF — directly from your terminal.**  
No subscriptions. No third-party servers. 100% runs on your computer.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Browser-Chromium-45ba4b?style=flat-square&logo=googlechrome&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Windows%20%7C%20Mac%20%7C%20Linux-✓-lightgrey?style=flat-square)](#)

</div>

---

## 🎯 What does it do?

It opens the Scribd document in a hidden browser, captures every page as a high-resolution image, and assembles them into a single PDF file — all automatically.

**What makes it different from other tools:**
- Uses Scribd's **embed viewer** — the cleanest, ad-free version of the document
- Captures **actual page elements**, not viewport screenshots (no sidebars, no cut-off content)
- **Strip-stitch algorithm** — for tall pages it scrolls in sections and stitches them together seamlessly
- **Auto-detects** the document's real access key from the page

---

## ⚡ Installation

### Step 1 — Make sure Python is installed

Download Python from [python.org](https://www.python.org/downloads/) if you don't have it.  
Open **CMD** (Windows) or **Terminal** (Mac/Linux) and check:
```
python --version
```
You should see something like `Python 3.11.0`.

### Step 2 — Install the required libraries

```bash
pip install playwright pymupdf pillow requests
playwright install chromium
```

> This downloads a small browser (Chromium) that the script uses to open Scribd pages. It's ~150MB and only happens once.

---

## 🍪 Get your Scribd cookies (required)

The script needs to log into Scribd as you, so it can access documents you have access to.

1. Install the **Cookie-Editor** extension:
   - Chrome → [Install here](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - Firefox → [Install here](https://addons.mozilla.org/firefox/addon/cookie-editor/)

2. Go to **[scribd.com](https://scribd.com)** and **log in** to your account

3. Click the Cookie-Editor icon in your browser toolbar

4. Click **"Export All"** → it copies the cookies to your clipboard

5. Open Notepad, paste, and save as **`cookies.json`**

---

## 🚀 How to use

Open CMD / Terminal, navigate to this folder, and run:

```bash
python src/scribd_downloader.py <SCRIBD_URL> --cookies cookies.json
```

**Real example:**
```bash
python src/scribd_downloader.py https://www.scribd.com/document/709322301/Presentation-Tipe --cookies cookies.json
```

That's it. The PDF will appear in a folder called `scribd_output/`.

---

## 📋 All options

| Option | What it does |
|--------|-------------|
| `--cookies cookies.json` | Your Scribd login cookies (needed for most documents) |
| `--images-only` | Save pages as separate JPEG images instead of making a PDF |

```bash
# Save as individual images instead of PDF
python src/scribd_downloader.py https://www.scribd.com/document/123456/Title --cookies cookies.json --images-only
```

---

## 📂 Output

After running, you'll find:

```
scribd_output/
├── My_Document_Title.pdf     ← your final PDF
└── images/
    ├── p0001.jpg             ← each page saved individually
    ├── p0002.jpg
    ├── p0003.jpg
    └── ...
```

---

## 🔧 Troubleshooting

**"No pages found"**
> The document didn't load. Make sure you exported cookies after logging in to Scribd, and that the document is publicly accessible.

**"Cookie warning: sameSite"**
> This is just a warning, not an error. The script handles it automatically and will still work fine.

**PDF pages are blank / white**
> The document was still loading when captured. Run the script again — it usually works on the second try.

**The script stops on a specific page**
> Open an [Issue](../../issues) with the document URL and the error message shown in the terminal.

---

## 🗂️ Project structure

```
scribd-downloader-pro/
│
├── src/
│   └── scribd_downloader.py   ← the main script (single file, no setup needed)
│
├── docs/                      ← screenshots and documentation images
├── README.md                  ← this file
├── requirements.txt           ← list of Python libraries needed
├── .gitignore                 ← tells Git what files to ignore
└── LICENSE                    ← MIT open source license
```

---

## ⚠️ Legal notice

This tool is intended for **personal backup purposes only** — for documents you have legitimate access to.  
Do not use it to distribute copyrighted material. The author is not responsible for misuse.  
Please respect [Scribd's Terms of Service](https://support.scribd.com/hc/en-us/articles/210129366).

---

<div align="center">
Made with ❤️ — Feel free to open issues or suggest improvements!
</div>
