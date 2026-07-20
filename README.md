# NRO APK Builder

Tự động patch `NROGame-bridge.apk` để kết nối server qua WebSocket bridge — **không cần Unity license**.

## Chạy workflow

**[Actions → Patch & Release NROGame APK → Run workflow](../../actions/workflows/patch-apk.yml)**

| Input | Default | Mô tả |
|-------|---------|-------|
| source_version | `v1.7.0` | Version APK gốc từ rem5 |
| target_host | `127.0.0.1` | IP server đích |
| target_port | `14445` | Port server đích |

→ ~2 phút → APK mới trong Releases

## Kiến trúc

```
[Android APK] → TCP 127.0.0.1:14445
                       ↓
              [ws_client_proxy.py]
                       ↓
              WebSocket → Game Server Java (Codespace)
```

## Cách patch hoạt động

1. Download APK gốc từ rem5 releases
2. Binary patch `global-metadata.dat` trong APK:
   - `nrofree.online` → `127.0.0.1`
3. Ký bằng debug keystore
4. Release tự động
