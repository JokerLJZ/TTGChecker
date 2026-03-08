# TTGChecker

基于 Python + Playwright + Firefox Profile 的 TTG 自动签到脚本。

## 功能

- 使用 Firefox 持久化 Profile 复用登录态，避免重复登录
- 启动后直接新建标签页访问 TTG，不关闭 Firefox 默认首标签页
- 使用真实页面元素定位与点击完成签到，并插入 1-3 秒随机等待
- 本地记录签到成功/失败状态，检测昨天和今天是否存在漏签
- 通过 WxPusher 发送成功通知或异常报警
- 支持通过 `headless` 开关切换有头/无头模式

## 目录

- `main.py`：CLI 入口
- `ttg_checker/config.py`：配置读取
- `ttg_checker/browser.py`：浏览器自动化与页面交互
- `ttg_checker/state.py`：签到状态记录
- `ttg_checker/notifier.py`：WxPusher 通知
- `ttg_checker/service.py`：签到流程编排
- `config.example.json`：配置样例

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox
```

## 配置

先复制示例配置：

```bash
cp config.example.json config.json
```

然后修改 `config.json` 中的以下字段：

- `browser.profile_path`：Firefox Profile 路径
- `browser.headless`：`true` 为无头，`false` 为有头
- `wxpusher.app_token`：WxPusher 应用 Token
- `wxpusher.uid`：消息接收 UID

### Firefox Profile 路径获取方法

在 Debian 13 上，Firefox Profile 通常位于：

```text
/home/<your-user>/.mozilla/firefox/
```

可以用下面的命令查看：

```bash
ls ~/.mozilla/firefox
```

常见结果类似：

```text
xxxxxxxx.default-release
profiles.ini
```

将 `browser.profile_path` 配置为类似 `/home/<your-user>/.mozilla/firefox/xxxxxxxx.default-release` 的目录。  
首次使用前，建议先用这个 Profile 手动登录 TTG，确认 Cookie 已保存在该 Profile 中。

## 运行

```bash
python3 main.py --config config.json
```

## 定时执行

可以使用 `cron` 每天定时执行，例如每天 08:30：

```cron
30 8 * * * cd /path/to/TTGChecker && /path/to/TTGChecker/.venv/bin/python main.py --config config.json
```

## 漏签说明

脚本会检查昨天和今天在本地状态文件中的执行结果。  
如果发现漏签，会立即触发重试，并在通知中标记漏签日期。

这里的“补签”是工程上的补救重试，不代表 TTG 支持对历史日期真正回补签到；若站点本身不提供历史补签入口，脚本只能对当前运行时刻再次尝试签到。
