# -*- mode: python ; coding: utf-8 -*-

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
        'sqlite3',
        'openpyxl',
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
