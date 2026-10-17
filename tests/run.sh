#!/bin/bash
# Lance tous les tests de l'appli (Playwright + Chromium). Code de sortie non nul au moindre échec.
cd "$(dirname "$0")"
OUT="${RS_OUT:-/tmp/rayon-sur-tests}"; mkdir -p "$OUT"
fail=0
for t in localisation.py navigation.py liens_drive.py magasins_reels.py appli.py bugs.py "robustesse.py 80"; do
  echo "──── $t"
  name="${t%% *}"
  timeout 1200 python3 $t > "$OUT/$name.log" 2>&1; rc=$?
  grep -v '^  ok ' "$OUT/$name.log"
  [ $rc = 0 ] || { fail=1; echo "!!! $name a échoué (code $rc)"; }
done
[ $fail = 0 ] && echo "TOUS LES TESTS SONT OK" || echo "AU MOINS UN TEST A ÉCHOUÉ"
exit $fail
