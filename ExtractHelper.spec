# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 显式收集 pymupdf 和 fitz
# 注意：pymupdf 安装后通常包名是 pymupdf，但也可能提供 fitz 顶层包
# collect_all 会返回 (datas, binaries, hiddenimports)
datas = []
binaries = []
hidden_imports = [
    'sklearn',
    'sklearn.utils._cython_blas',
    'sklearn.neighbors.typedefs',
    'sklearn.neighbors.quad_tree',
    'sklearn.tree',
    'sklearn.tree._utils',
    'sentence_transformers',
    'faiss',
    'numpy',
    'torch',
    'app',
    'app.app_core',
    'app.config',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'shiboken6',
]

# 尝试收集 pymupdf
try:
    tmp_ret = collect_all('pymupdf')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hidden_imports += tmp_ret[2]
except Exception:
    pass

# 尝试收集 fitz (旧版或某些发行版)
try:
    tmp_ret = collect_all('fitz')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hidden_imports += tmp_ret[2]
except Exception:
    pass

a = Analysis(['app\\gui\\main_window.py'],
             pathex=['D:\\Code\\Project\\ExtractHelper'],
             binaries=binaries,
             datas=datas,
             hiddenimports=hidden_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='ExtractHelper',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False ) # windowed mode
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ExtractHelper')
