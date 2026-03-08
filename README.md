# TTGChecker

基于 Python + Playwright + Chrome 用户数据目录的 TTG 自动签到脚本。

## 功能

- 使用 Chrome 持久化用户数据目录复用登录态，避免重复登录
- 脚本自动启动 Chrome，新建标签页访问 TTG，完成后主动关闭 Chrome
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
playwright install chrome
```

## 配置

先复制示例配置：

```bash
cp config.example.json config.json
```

然后修改 `config.json` 中的以下字段：

- `browser.user_data_dir`：Chrome 用户数据目录
- `browser.channel`：默认用 `chrome`
- `browser.executable_path`：可选，自定义 Chrome 可执行文件路径
- `browser.headless`：`true` 为无头，`false` 为有头
- `wxpusher.app_token`：WxPusher 应用 Token
- `wxpusher.uid`：消息接收 UID

### Chrome 用户数据目录获取方法

在 Debian 13 上，Google Chrome 用户数据目录通常位于：

```text
/home/<your-user>/.config/google-chrome
```

可以用下面的命令查看：

```bash
ls ~/.config/google-chrome
```

常见会包含：

```text
Default
Local State
First Run
```

将 `browser.user_data_dir` 配置为类似 `/home/<your-user>/.config/google-chrome` 的目录。  
首次使用前，建议先用这个 Chrome 用户数据目录手动登录 TTG，确认 Cookie 已保存在该目录中。

如果系统里的 Chrome 不是标准安装路径，可以额外配置 `browser.executable_path`，例如：

```json
"executable_path": "/usr/bin/google-chrome"
```

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
