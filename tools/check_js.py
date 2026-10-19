#!/usr/bin/env python3
"""Vérifie la syntaxe du JavaScript de index.html : extrait les blocs <script> et lance node --check."""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
js = '\n;\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(js)
r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
os.unlink(f.name)
if r.returncode:
    print(r.stderr.strip())
    sys.exit(1)
print('JavaScript OK')
