import os
import sys
import shutil
import zipfile
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def find_inno_compiler():
    """Finds Inno Setup command-line compiler (iscc.exe)."""
    candidates = [
        shutil.which('iscc'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Inno Setup 6', 'ISCC.exe'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'Inno Setup 6', 'ISCC.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Inno Setup 6', 'ISCC.exe'),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None

def find_runtime_dlls():
    """Finds required Visual C++ runtime DLLs for bundling."""
    dlls = {}
    
    # 1. vcruntime140_1.dll (required by 64-bit Python 3.11)
    py_vc1 = os.path.join(sys.base_prefix, 'vcruntime140_1.dll')
    sys_vc1 = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'vcruntime140_1.dll')
    if os.path.isfile(py_vc1):
        dlls['vcruntime140_1.dll'] = py_vc1
    elif os.path.isfile(sys_vc1):
        dlls['vcruntime140_1.dll'] = sys_vc1

    # 2. msvcp140.dll
    sys_msvcp = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'msvcp140.dll')
    if os.path.isfile(sys_msvcp):
        dlls['msvcp140.dll'] = sys_msvcp

    return dlls

def build_app():
    print("=" * 60)
    print("       Building Omni Downloader v1.0.1 Standalone & Installer")
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
        '-y'
    ]

    # Add app icon
    ico_path = os.path.join(PROJECT_ROOT, 'app.ico')
    if os.path.exists(ico_path):
        cmd.extend(['--icon', ico_path])
        cmd.extend(['--add-data', f'app.ico{sep}.'])

    # Add version info if present
    ver_path = os.path.join(PROJECT_ROOT, 'version_info.txt')
    if os.path.exists(ver_path):
        cmd.extend(['--version-file', ver_path])

    # Add runtime DLLs directly to PyInstaller binaries
    runtime_dlls = find_runtime_dlls()
    for name, path in runtime_dlls.items():
        print(f"[*] Bundling C++ runtime dependency: {name} -> {path}")
        cmd.extend(['--add-binary', f'{path}{sep}.'])

    cmd.append(os.path.join(PROJECT_ROOT, 'desktop.py'))

    print(f"\n[*] Running PyInstaller compilation...")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print("[ERROR] PyInstaller compilation failed.")
        return False

    # 4. Copy engine binaries into output distribution
    source_bin = os.path.join(PROJECT_ROOT, 'bin')
    target_bin = os.path.join(output_app_dir, 'bin')
    if os.path.exists(source_bin):
        print(f"[*] Packaging engine binaries (bin/) into distribution...")
        shutil.copytree(source_bin, target_bin, dirs_exist_ok=True)
    else:
        os.makedirs(target_bin, exist_ok=True)

    # Copy runtime DLLs to output directory root and _internal to ensure OS loader finds them
    internal_dir = os.path.join(output_app_dir, '_internal')
    for name, path in runtime_dlls.items():
        try:
            shutil.copy2(path, os.path.join(output_app_dir, name))
            if os.path.isdir(internal_dir):
                shutil.copy2(path, os.path.join(internal_dir, name))
        except Exception as e:
            print(f"[!] Warning copying {name}: {e}")

    # Copy README.md, LICENSE, and app.ico
    for f in ('README.md', 'LICENSE', 'app.ico'):
        src = os.path.join(PROJECT_ROOT, f)
        if os.path.exists(src):
            shutil.copy2(src, output_app_dir)

    # 5. Create ready-to-distribute ZIP archive
    zip_output_path = os.path.join(dist_dir, 'OmniDownloader-v1.0.1-Windows.zip')
    print(f"[*] Packaging into portable ZIP: {zip_output_path}...")
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_app_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)

    # 6. Build Inno Setup Installer (.exe) if compiler is available
    iscc = find_inno_compiler()
    installer_path = None
    if iscc and os.path.isfile(os.path.join(PROJECT_ROOT, 'installer.iss')):
        print(f"\n[*] Found Inno Setup compiler: {iscc}")
        print(f"[*] Compiling professional Windows Installer wizard...")
        iscc_cmd = [iscc, os.path.join(PROJECT_ROOT, 'installer.iss')]
        res = subprocess.run(iscc_cmd, cwd=PROJECT_ROOT)
        if res.returncode == 0:
            installer_path = os.path.join(dist_dir, 'OmniDownloader-Setup-v1.0.1.exe')
            print(f" [SUCCESS] Windows Installer created: {installer_path}")
        else:
            print("[!] Inno Setup compilation encountered a warning/error.")
    else:
        print("[!] Inno Setup compiler not found. Skipping installer exe generation.")

    # 7. Clean up intermediate build directory
    if os.path.exists(build_dir):
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(" [SUCCESS] Omni Downloader v1.0.1 compilation finished!")
    print(f" Standalone folder: {output_app_dir}")
    print(f" Portable ZIP:      {zip_output_path}")
    if installer_path and os.path.exists(installer_path):
        print(f" Setup Installer:   {installer_path}")
    print("=" * 60)
    return True

if __name__ == '__main__':
    build_app()
