#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def run_command(cmd: list[str], cwd: Path | None = None) -> bool:
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=False,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        return False


def clean_build_files(project_root: Path) -> None:
    print("清理临时文件...")
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  已删除: {dir_path}")
    
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            print(f"  已删除: {pycache}")


def install_dependencies(project_root: Path) -> bool:
    print("\n安装依赖...")
    requirements_path = project_root / "requirements.txt"
    return run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_path), "-U"])


def get_spec_file(project_root: Path, system: str | None = None) -> Path:
    if system is None:
        system = platform.system()
    
    if system == "Darwin":
        spec_file = project_root / "build_scripts" / "AutoApiTest-mac.spec"
        if not spec_file.exists():
            spec_file = create_mac_spec(project_root)
        return spec_file
    else:
        return project_root / "build_scripts" / "AutoApiTest.spec"


def create_mac_spec(project_root: Path) -> Path:
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../src/main.py'],
    pathex=['../'],
    binaries=[],
    datas=[
        ('../src', 'src'),
        ('../data', 'data'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'httpx',
        'openai',
        'yaml',
        'pytest',
        'allure',
        'jsonpath_ng',
        'jsonpath_ng.ext',
        'ui',
        'ui.main_window',
        'ui.pages',
        'ui.pages.base_page',
        'ui.pages.test_case_page',
        'ui.pages.test_script_page',
        'ui.pages.ai_model_page',
        'core',
        'core.test_case_service',
        'core.test_script_service',
        'core.ai_model_service',
        'core.export_service',
        'core.code_validator',
        'models',
        'models.test_case',
        'models.test_script',
        'models.ai_model',
        'models.database',
        'ai',
        'ai.client',
        'ai.prompts',
        'utils',
        'utils.config',
        'utils.logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoApiTest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

app = BUNDLE(
    exe,
    name='AutoApiTest.app',
    icon=None,
    bundle_identifier='com.autotest.AutoApiTest',
    info_plist={
        'CFBundleName': 'AutoApiTest',
        'CFBundleDisplayName': 'AutoApiTest',
        'CFBundleIdentifier': 'com.autotest.AutoApiTest',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleExecutable': 'AutoApiTest',
        'LSMinimumSystemVersion': '10.13',
        'NSHighResolutionCapable': True,
    },
)
'''
    spec_file = project_root / "build_scripts" / "AutoApiTest-mac.spec"
    spec_file.write_text(spec_content, encoding='utf-8')
    print(f"已创建 macOS spec 文件: {spec_file}")
    return spec_file


def build_executable(project_root: Path, system: str | None = None) -> bool:
    print("\n开始打包...")
    
    if system is None:
        system = platform.system()
    
    spec_file = get_spec_file(project_root, system)
    
    if not spec_file.exists():
        print(f"错误: 找不到 spec 文件: {spec_file}")
        return False
    
    return run_command(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"],
        cwd=project_root,
    )


def print_build_result(project_root: Path, system: str | None = None) -> None:
    if system is None:
        system = platform.system()
    
    dist_dir = project_root / "dist"
    
    print("\n" + "=" * 50)
    print("打包完成!")
    print("=" * 50)
    
    if system == "Darwin":
        app_path = dist_dir / "AutoApiTest.app"
        if app_path.exists():
            size_mb = app_path.stat().st_size / (1024 * 1024)
            print(f"应用程序: {app_path}")
            print(f"大小: {size_mb:.2f} MB")
    else:
        exe_path = dist_dir / "AutoApiTest.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"可执行文件: {exe_path}")
            print(f"文件大小: {size_mb:.2f} MB")
    
    if not exe_path.exists() if system != "Darwin" else not app_path.exists():
        print(f"输出目录: {dist_dir}")
        if dist_dir.exists():
            for item in dist_dir.iterdir():
                print(f"  - {item.name}")


def main() -> int:
    build_scripts_dir = Path(__file__).parent.resolve()
    project_root = build_scripts_dir.parent.resolve()
    current_system = platform.system()
    
    system_name = "macOS" if current_system == "Darwin" else "Windows"
    
    print("=" * 50)
    print(f"AutoApiTest 打包脚本 ({system_name})")
    print("=" * 50)
    print(f"项目目录: {project_root}")
    print(f"脚本目录: {build_scripts_dir}")
    print(f"当前平台: {current_system}")
    
    clean_build_files(project_root)
    
    if not install_dependencies(project_root):
        print("错误: 依赖安装失败")
        return 1
    
    if not build_executable(project_root, current_system):
        print("错误: 打包失败")
        return 1
    
    print_build_result(project_root, current_system)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
