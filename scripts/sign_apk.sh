#!/bin/bash
set -e
APK_UNSIGNED=$1
APK_SIGNED=${2:-NROGame-bridge-patched.apk}

echo "[*] Tạo debug keystore..."
keytool -genkey -v -keystore debug.keystore -alias debug \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Debug, OU=Debug, O=Debug, L=Debug, S=Debug, C=US" \
  -storepass android -keypass android 2>/dev/null

echo "[*] Ký APK với debug key..."
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore debug.keystore -storepass android -keypass android \
  -signedjar "$APK_SIGNED" "$APK_UNSIGNED" debug

echo "[✓] Đã ký: $APK_SIGNED"
