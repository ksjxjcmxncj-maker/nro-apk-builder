#!/bin/bash
set -e
APK_UNSIGNED=$1
APK_SIGNED=${2:-NROGame-bridge-patched.apk}

# Tìm build-tools mới nhất trong Android SDK
BUILD_TOOLS=$(ls -d "$ANDROID_HOME/build-tools"/* 2>/dev/null | sort -V | tail -1)
if [ -z "$BUILD_TOOLS" ]; then
  echo "[!] Không tìm thấy build-tools, thử cài..."
  yes | sdkmanager "build-tools;35.0.0" > /dev/null 2>&1
  BUILD_TOOLS=$(ls -d "$ANDROID_HOME/build-tools"/* | sort -V | tail -1)
fi
echo "[*] Build-tools: $BUILD_TOOLS"

# 1. XOÁ TOÀN BỘ chữ ký cũ (fix: double-signature bug)
echo "[*] Xoá chữ ký cũ (NRO.*, DEBUG.*, MANIFEST.MF)..."
cp "$APK_UNSIGNED" apk_clean.apk
zip -d apk_clean.apk 'META-INF/*' 2>/dev/null || true
echo "    META-INF sau khi xoá: $(unzip -l apk_clean.apk 'META-INF/*' 2>/dev/null | grep -c '\.SF\|\.RSA\|\.DSA') sig files (expect 0)"

# 2. ZIPALIGN trước khi ký (bắt buộc)
echo "[*] Zipalign 4-byte..."
"$BUILD_TOOLS/zipalign" -f -v 4 apk_clean.apk apk_aligned.apk
echo "    Zipalign verify: $("$BUILD_TOOLS/zipalign" -c -v 4 apk_aligned.apk 2>&1 | tail -1)"

# 3. Tạo keystore
echo "[*] Tạo debug keystore..."
keytool -genkey -v \
  -keystore debug.keystore -alias nrokey \
  -keyalg RSA -keysize 2048 -validity 36500 \
  -dname "CN=NRO, OU=NRO, O=NRO, L=HN, S=HN, C=VN" \
  -storepass nropass -keypass nropass 2>/dev/null

# 4. KÝ bằng apksigner — v1 + v2 + v3 (fix: jarsigner chỉ có v1)
echo "[*] apksigner (v1+v2+v3)..."
"$BUILD_TOOLS/apksigner" sign \
  --ks debug.keystore \
  --ks-key-alias nrokey \
  --ks-pass pass:nropass \
  --key-pass pass:nropass \
  --v1-signing-enabled true \
  --v2-signing-enabled true \
  --v3-signing-enabled true \
  --out "$APK_SIGNED" \
  apk_aligned.apk

# 5. VERIFY
echo "[*] Verify chữ ký..."
"$BUILD_TOOLS/apksigner" verify --verbose --print-certs "$APK_SIGNED" 2>&1 \
  | grep -E "Verified|v[123] scheme|Signer"

SIZE=$(du -h "$APK_SIGNED" | cut -f1)
echo "[✓] Done: $APK_SIGNED ($SIZE)"