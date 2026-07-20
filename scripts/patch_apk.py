#!/usr/bin/env python3
"""
Patch NROGame-bridge.apk:
- Thay nrofree.online → 127.0.0.1 trong global-metadata.dat
- Thử decode ipString (XOR-69) và encode lại với IP mới
"""
import sys, os, zipfile, re

APK_IN   = sys.argv[1]
APK_OUT  = sys.argv[2]
NEW_IP   = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
NEW_PORT = sys.argv[4] if len(sys.argv) > 4 else "14445"

METADATA_PATH = "assets/bin/Data/Managed/Metadata/global-metadata.dat"

def xor_decode(s, key=69):
    try:
        return "".join(chr(int(x) ^ key) for x in s.split(","))
    except:
        return ""

def xor_encode(s, key=69):
    return ",".join(str(ord(c) ^ key) for c in s)

def patch_metadata(data: bytes) -> bytes:
    patched = bytearray(data)
    changed = 0

    # 1. Plain-text patch: nrofree.online → 127.0.0.1 (pad với null)
    old_domain = b"nrofree.online"
    new_domain  = NEW_IP.encode()
    if len(new_domain) < len(old_domain):
        new_domain = new_domain + b"\x00" * (len(old_domain) - len(new_domain))
    idx = 0
    while True:
        pos = bytes(patched).find(old_domain, idx)
        if pos == -1: break
        patched[pos:pos+len(old_domain)] = new_domain[:len(old_domain)]
        print(f"  [plain] nrofree.online → {NEW_IP} @ 0x{pos:x}")
        changed += 1
        idx = pos + 1

    # 2. Encoded ipString: tìm comma-separated XOR-69 patterns
    text = data.decode("latin-1")
    pattern = re.compile(r'((?:\d{1,3},){8,}\d{1,3})')
    for m in pattern.finditer(text):
        try:
            decoded = xor_decode(m.group())
            if any(kw in decoded for kw in ["nrofree", "14445", "LocalHost"]):
                print(f"  [encoded] @ 0x{m.start():x}: decoded={decoded[:80]}")
                parts = decoded.split(":")
                if len(parts) >= 3:
                    flags = parts[-1] if len(parts) >= 4 else "0,0,0"
                    new_conn = f"LocalHost:{NEW_IP}:{NEW_PORT}:{flags}"
                else:
                    new_conn = f"LocalHost:{NEW_IP}:{NEW_PORT}:0,0,0"
                new_enc = xor_encode(new_conn).encode("latin-1")
                old_enc = m.group().encode("latin-1")
                pos = m.start()
                if len(new_enc) <= len(old_enc):
                    pad = b" " * (len(old_enc) - len(new_enc))
                    patched[pos:pos+len(old_enc)] = new_enc + pad
                    print(f"  [patch]  → {new_conn}")
                    changed += 1
                else:
                    print(f"  [skip]  new len {len(new_enc)} > old {len(old_enc)}")
        except:
            pass

    print(f"[*] Total patches in metadata: {changed}")
    return bytes(patched)

print(f"[*] Input:  {APK_IN}")
print(f"[*] Output: {APK_OUT}")
print(f"[*] Target: {NEW_IP}:{NEW_PORT}")

with zipfile.ZipFile(APK_IN, 'r') as zin:
    with zipfile.ZipFile(APK_OUT, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == METADATA_PATH:
                print(f"[*] Patching {METADATA_PATH} ({len(data):,} bytes)...")
                data = patch_metadata(data)
            zout.writestr(item, data)

size = os.path.getsize(APK_OUT)
print(f"[✓] Done: {APK_OUT} ({size:,} bytes)")
