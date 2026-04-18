# TTGChecker

TTG（totheglory.im）每日自动签到。**不使用浏览器自动化**，直接用 `curl_cffi` 模拟真实 Edge/Chrome 的 TLS + HTTP/2 指纹发请求，规避 TTG 的反脚本检测。

## 工作原理

TTG 主页 inline JS 内嵌了 `signed_timestamp`（10 位时间戳）和 `signed_token`（32 位 md5），点击签到时由 jQuery 发起：

```
POST https://totheglory.im/signed.php
body: signed_timestamp=...&signed_token=...
```

脚本流程：

1. `GET /` 拉取主页（带 cookie + 真实 Edge TLS 指纹）
2. 用正则从主页 HTML 解析 `signed_timestamp` 与 `signed_token`
3. 随机停顿 1.2-3.4s（拟人节奏）
4. `POST /signed.php` 提交签到
5. 解析返回，记录状态，发 WxPusher 通知

之前 `requests` 直接 GET URL 失败的原因：① TLS 指纹被识别为 Python；② 没先访问主页拿一次性 token。本实现两个问题都解决了。

## 安装（Debian 13）

```bash
sudo useradd -r -m -d /opt/ttg-checker ttg
sudo -u ttg git clone <this-repo> /opt/ttg-checker
cd /opt/ttg-checker
sudo -u ttg python3 -m venv .venv
sudo -u ttg .venv/bin/pip install -r requirements.txt
```

## 配置

```bash
cp config.example.json config.json
chmod 600 config.json
```

填写：

| 字段 | 说明 |
|---|---|
| `ttg.cookie` | 浏览器 F12 → Network → 任一 totheglory.im 请求 → Headers → Request Headers → 整段 `Cookie:` 的值 |
| `ttg.user_agent` | 同一个浏览器的 User-Agent。**必须和 cookie 来自同一浏览器**，否则可能触发安全校验 |
| `ttg.impersonate` | curl_cffi 的伪装目标。Edge 用 `edge99`，Chrome 用 `chrome120` |
| `wxpusher.app_token` / `wxpusher.uid` | WxPusher 通知凭据 |

### 获取 Cookie 的方法

1. 用 Edge / Chrome 登录 https://totheglory.im
2. F12 → Network 面板
3. 刷新页面
4. 点列表中第一条请求（域名 `totheglory.im`）
5. 切到 Headers → Request Headers → 找 `Cookie:` 那一行
6. 右键复制整行的值（不要带 `Cookie:` 这几个字）粘进 `config.json`

Cookie 失效时（一般几个月一次，或更换 IP/UA 后）会触发 WxPusher 报警 "TTG Cookie 失效"，重复以上步骤更新即可。

## 手动测试

```bash
.venv/bin/python main.py --config config.json
```

成功会打印 "签到成功。站点反馈: ..."，并在 `data/checkin_log.json` 写入记录。

## 部署 systemd 定时任务

```bash
sudo cp deploy/ttg-checker.service /etc/systemd/system/
sudo cp deploy/ttg-checker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ttg-checker.timer
```

查看下次触发时间：

```bash
systemctl list-timers ttg-checker.timer
```

查看日志：

```bash
journalctl -u ttg-checker.service -n 100
```

## 状态文件

`data/checkin_log.json` 结构：

```json
{
  "history": {
    "2026-04-18": {"run_at": "...", "success": true, "message": "...", "missed_dates": []}
  },
  "last_success_date": "2026-04-18",
  "last_run_at": "..."
}
```

漏签检测：每次执行会检查最近 7 天内 `success != true` 的日期，写入通知正文（TTG 不支持补签，仅作为提示）。

## 反爬要点

- TLS/HTTP2 指纹由 `curl_cffi` 伪装为 Edge/Chrome（基于 curl-impersonate）
- 必先 GET 主页拿到当前刷新周期的 token，不直接打接口
- POST 时带齐 `Origin` / `Referer` / `X-Requested-With: XMLHttpRequest` / `Sec-Fetch-*`
- 主页和签到之间随机停顿 1.2-3.4s
- systemd timer 用 `RandomizedDelaySec=30min` + 脚本内 `--jitter-seconds 1800` 双重打散，避免每天同一秒触发
- **不要**在多台机器上用同一个 cookie，TTG 会检测异地登录
