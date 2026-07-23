#!/usr/bin/env bash
# Verifica que un AppImage pueda correr en distros mas viejas que la de build.
#
# Existe porque este es justo el fallo que no se detecta probando en tu propio
# equipo: el AppImage funciona perfecto donde lo compilaste y no arranca en
# ningun otro lado. Correr esto antes de publicar una release.
set -uo pipefail

APPIMAGE="${1:-releases/HarmoNiq-x86_64.AppImage}"
[ -f "${APPIMAGE}" ] || { echo "No existe ${APPIMAGE}"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

( cd "${TMP}" && "$(realpath "${OLDPWD}/${APPIMAGE}" 2>/dev/null || realpath "${APPIMAGE}")" --appimage-extract >/dev/null 2>&1 )
ROOT="${TMP}/squashfs-root"
[ -d "${ROOT}" ] || { echo "No se pudo extraer el AppImage"; exit 1; }

# Version de glibc mas alta que exige cualquier binario del bundle.
MAX="$(find "${ROOT}" -type f \( -name '*.so' -o -name '*.so.*' -o -perm -u+x \) -print0 2>/dev/null \
    | xargs -0 -r -n 20 objdump -T 2>/dev/null \
    | grep -oE 'GLIBC_[0-9]+\.[0-9]+' | sort -uV | tail -1)"

echo "glibc maxima requerida: ${MAX:-ninguna}"

VER="${MAX#GLIBC_}"
echo
echo "Compatibilidad estimada:"
check() { # $1=nombre  $2=glibc de esa distro
    if [ "$(printf '%s\n%s\n' "${VER}" "$2" | sort -V | head -1)" = "${VER}" ]; then
        echo "  OK    $1 (glibc $2)"
    else
        echo "  FALLA $1 (glibc $2) - no va a arrancar"
    fi
}
check "Linux Mint 21 / Ubuntu 22.04" 2.35
check "Linux Mint 22 / Ubuntu 24.04" 2.39
check "Debian 12 bookworm"           2.36
check "Fedora 40"                    2.39

echo
echo "Plugins de plataforma Qt encontrados:"
find "${ROOT}" -path '*plugins/platforms/*.so' -printf '  %f\n' 2>/dev/null | sort || echo "  NINGUNO (la app no abrira ventana)"

echo
echo "QtWebEngineProcess:"
if find "${ROOT}" -name 'QtWebEngineProcess' -print -quit 2>/dev/null | grep -q .; then
    echo "  presente"
else
    echo "  FALTA - la ventana quedara en blanco"
fi

echo
echo "ffmpeg empaquetado:"
find "${ROOT}" -name 'ffmpeg' -type f -print -quit 2>/dev/null | grep -q . \
    && echo "  presente" || echo "  ausente (se descargara en el primer uso)"
