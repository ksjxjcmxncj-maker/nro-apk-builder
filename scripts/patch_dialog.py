#!/usr/bin/env python3
"""
Patch smali của UnityPlayerActivity để tự động gọi UnitySendMessage
sau khi Unity khởi động, bỏ qua dialog nhập IP/Port (AddressScr).

Cách hoạt động:
1. Tạo file NroAutoConnectRunnable.smali (Runnable chạy trong Thread riêng)
2. Inject vào onResume() của UnityPlayerActivity để spawn thread 1 lần
   → Thread sleep 5s rồi gọi UnityPlayer.UnitySendMessage("AddressScr","doConnect","")
"""
import os, sys, re

APKTOOL_DIR = sys.argv[1]

# ── Tìm UnityPlayerActivity.smali ──────────────────────────────────────────
smali_path = None
smali_dir  = None
for root, dirs, files in os.walk(APKTOOL_DIR):
    for f in files:
        if f == "UnityPlayerActivity.smali":
            smali_path = os.path.join(root, f)
            smali_dir  = root
            break
    if smali_path:
        break

if not smali_path:
    print("ERROR: UnityPlayerActivity.smali not found!")
    sys.exit(1)

print(f"[*] Found smali: {smali_path}")

# ── Tạo NroAutoConnectRunnable.smali ───────────────────────────────────────
# Đây là Runnable: sleep 5s, rồi thử doConnect + autoLogin + doLogin trên nhiều GO
RUNNABLE_SMALI = """.class public Lcom/unity3d/player/NroAutoConnectRunnable;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public run()V
    .registers 4

    # Sleep 5000ms cho Unity khởi động xong
    :try_sleep_start
    const-wide/32 v0, 0x1388
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    :try_sleep_end
    .catch Ljava/lang/Exception; {:try_sleep_start .. :try_sleep_end} :catch_sleep
    goto :after_sleep
    :catch_sleep
    move-exception v0
    :after_sleep

    # Thử 1: AddressScr::doConnect
    :try_1_start
    const-string v0, "AddressScr"
    const-string v1, "doConnect"
    const-string v2, ""
    invoke-static {v0, v1, v2}, Lcom/unity3d/player/UnityPlayer;->UnitySendMessage(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    :try_1_end
    .catch Ljava/lang/Exception; {:try_1_start .. :try_1_end} :catch_1
    :catch_1

    # Thử 2: AddressScr::doLogin
    :try_2_start
    const-string v0, "AddressScr"
    const-string v1, "doLogin"
    const-string v2, ""
    invoke-static {v0, v1, v2}, Lcom/unity3d/player/UnityPlayer;->UnitySendMessage(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    :try_2_end
    .catch Ljava/lang/Exception; {:try_2_start .. :try_2_end} :catch_2
    :catch_2

    # Thử 3: AddressScr::autoLogin
    :try_3_start
    const-string v0, "AddressScr"
    const-string v1, "autoLogin"
    const-string v2, ""
    invoke-static {v0, v1, v2}, Lcom/unity3d/player/UnityPlayer;->UnitySendMessage(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    :try_3_end
    .catch Ljava/lang/Exception; {:try_3_start .. :try_3_end} :catch_3
    :catch_3

    # Thử 4: ServerListScreen::doConnect (fallback)
    :try_4_start
    const-string v0, "ServerListScreen"
    const-string v1, "doConnect"
    const-string v2, ""
    invoke-static {v0, v1, v2}, Lcom/unity3d/player/UnityPlayer;->UnitySendMessage(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    :try_4_end
    .catch Ljava/lang/Exception; {:try_4_start .. :try_4_end} :catch_4
    :catch_4

    return-void
.end method
"""

runnable_path = os.path.join(smali_dir, "NroAutoConnectRunnable.smali")
with open(runnable_path, "w") as f:
    f.write(RUNNABLE_SMALI)
print(f"[*] Created: {runnable_path}")

# ── Đọc và patch UnityPlayerActivity.smali ─────────────────────────────────
with open(smali_path) as f:
    content = f.read()

# Thêm static field mNroAutoConnected
FIELD_DECL = ".field private static mNroAutoConnected:Z\n"
if "mNroAutoConnected" not in content:
    # Thêm sau dòng .class
    content = re.sub(
        r'(\.class [^\n]+\n)',
        r'\1' + FIELD_DECL,
        content,
        count=1
    )
    print("[*] Added static field mNroAutoConnected")
else:
    print("[*] Field mNroAutoConnected already exists")

# Code inject vào cuối onResume (trước return-void)
INJECT_CODE = """
    # === NRO AUTO-CONNECT PATCH (injected) ===
    # Chỉ chạy 1 lần khi game mở lần đầu
    sget-boolean v0, Lcom/unity3d/player/UnityPlayerActivity;->mNroAutoConnected:Z
    if-nez v0, :nro_already_done
    const/4 v0, 0x1
    sput-boolean v0, Lcom/unity3d/player/UnityPlayerActivity;->mNroAutoConnected:Z
    new-instance v0, Ljava/lang/Thread;
    new-instance v1, Lcom/unity3d/player/NroAutoConnectRunnable;
    invoke-direct {v1}, Lcom/unity3d/player/NroAutoConnectRunnable;-><init>()V
    invoke-direct {v0, v1}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {v0}, Ljava/lang/Thread;->start()V
    :nro_already_done
    # === END PATCH ===
"""

def inject_into_method(content, method_name):
    """Tìm method và inject code trước return-void cuối cùng."""
    # Pattern: tìm method declaration
    method_pat = re.compile(
        rf'(\.method [^\n]*{re.escape(method_name)}\(\)[^\n]*\n.*?)(    return-void\n\.end method)',
        re.DOTALL
    )
    m = method_pat.search(content)
    if not m:
        print(f"[!] Method {method_name} not found")
        return content, False

    orig = m.group(0)
    # Chỉ inject nếu chưa có patch
    if "nro_already_done" in orig:
        print(f"[*] {method_name}: already patched")
        return content, True

    patched = m.group(1) + INJECT_CODE + "    return-void\n.end method"
    new_content = content[:m.start()] + patched + content[m.end():]
    print(f"[*] Injected into {method_name}")
    return new_content, True

content, ok1 = inject_into_method(content, "onResume")
if not ok1:
    # Fallback: inject vào onCreate
    content, ok2 = inject_into_method(content, "onCreate")
    if ok2:
        print("[*] Injected into onCreate (onResume fallback)")

with open(smali_path, "w") as f:
    f.write(content)

print("[OK] smali patch complete")
print(f"     NroAutoConnectRunnable: {runnable_path}")
print(f"     UnityPlayerActivity patched: {smali_path}")
