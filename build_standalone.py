import os
import sys
import shutil
import zipfile
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def build_app():
    print("=" * 60)
    print("       Building Omni Downloader v1.0 Standalone App")
    print("=" * 60)

    # 1. Ensure pyinstaller is available
    pyinstaller_exe = shutil.which('pyinstaller')
    if not pyinstaller_exe:
        venv_pyinstaller = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'pyinstaller.exe')
        if os.path.exists(venv_pyinstaller):
            pyinstaller_exe = venv_pyinstaller
        else:
            print("[ERROR] PyInstaller not found. Please install it with: pip install pyinstaller")
            return False

    # 2. Build directories
    dist_dir = os.path.join(PROJECT_ROOT, 'dist')
    build_dir = os.path.join(PROJECT_ROOT, 'build')
    output_app_dir = os.path.join(dist_dir, 'OmniDownloader')

    # Clean previous build artifacts
    if os.path.exists(output_app_dir):
        shutil.rmtree(output_app_dir, ignore_errors=True)

    # 3. Construct PyInstaller command
    # Windows uses semicolon for add-data
    sep = ';' if os.name == 'nt' else ':'
    cmd = [
        pyinstaller_exe,
        '--noconsole',
        '--onedir',
        '--name', 'OmniDownloader',
        '--add-data', f'templates{sep}templates',
        '--add-data', f'static{sep}static',
        '--collect-all', 'webview',
        '--collect-all', 'yt_dlp',
        '--collect-all', 'imageio_ffmpeg',
        '--distpath', dist_dir,
        '--workpath', build_dir,
        '--clean',
        '-y',
        os.path.join(PROJECT_ROOT, 'desktop.py')
    ]

    print(f"[*] Running PyInstaller compilation...")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print("[ERROR] PyInstaller compilation failed.")
        return False

    # 4. Copy bin/ folder into the packaged output
    source_bin = os.path.join(PROJECT_ROOT, 'bin')
    target_bin = os.path.join(output_app_dir, 'bin')
    if os.path.exists(source_bin):
        print(f"[*] Packaging engine binaries (bin/) into distribution...")
        shutil.copytree(source_bin, target_bin, dirs_exist_ok=True)
    else:
        os.makedirs(target_bin, exist_ok=True)

    # Copy README.md and LICENSE
    for f in ('README.md', 'LICENSE'):
        src = os.path.join(PROJECT_ROOT, f)
        if os.path.exists(src):
            shutil.copy2(src, output_app_dir)

    # 5. Create ready-to-distribute ZIP archive
    zip_output_path = os.path.join(dist_dir, 'OmniDownloader-v1.0.0-Windows.zip')
    print(f"[*] Packaging into distribution ZIP: {zip_output_path}...")
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_app_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)

    # 6. Clean up intermediate build directory
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(" [SUCCESS] Omni Downloader v1.0 standalone build completed!")
    print(f" Output folder: {output_app_dir}")
    print(f" Release ZIP:   {zip_output_path}")
    print("=" * 60)
    return True

if __name__ == '__main__':
    build_app()
