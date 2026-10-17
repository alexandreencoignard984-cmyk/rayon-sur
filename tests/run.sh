#!/bin/bash
# Lance tous les tests de l'appli (Playwright + Chromium). Code de sortie non nul au moindre échec.
cd "$(dirname "$0")"
OUT="${RS_OUT:-/tmp/rayon-sur-tests}"; mkdir -p "$OUT"
fail=0
for t in localisation.py liens_drive.py magasins_reels.py appli.py; do
  echo "──── $t"
  timeout 600 python3 "$t" > "$OUT/$t.log" 2>&1; rc=$?
  grep -v '^  ok ' "$OUT/$t.log"
  [ $rc = 0 ] || { fail=1; echo "!!! $t a échoué (code $rc)"; }
done
[ $fail = 0 ] && echo "TOUS LES TESTS SONT OK" || echo "AU MOINS UN TEST A ÉCHOUÉ"
exit $fail
