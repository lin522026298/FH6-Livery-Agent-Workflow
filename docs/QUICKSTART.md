# 安装与首轮使用

## 用户

将仓库链接、主题、精确车型和参考图交给 Agent 即可。告诉它先读 `AGENTS.md`。你不需要写下面的命令或理解图层格式；这些是给 Agent 使用的。

完整流程需要 Agent 能操作一台 Windows x64 电脑并查看图片，电脑上有用户自己的 FH6 资源。纯聊天窗口若没有本地工具能力，可负责方案和提示词，制作/上车步骤需连接有本地能力的 Agent。生图可使用已有订阅内置工具，不要求另买特定 API；也可把 Agent 提供的提示词/参考交给生图产品，再传回原图。

角色默认忠实于官方原始形象和指定形态。用户的特殊改编要求优先。方案、母稿、拟合和上车均可能需要多轮视觉审查、截图圈线和交互式修改。任何部分都可以返工，已交付也可继续改。

## Agent：初始化

检出仓库或解压源码到独立目录，不将用户项目放在仓库内。使用普通用户权限：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1 -Workspace C:\LiveryProjects
```

`-Workspace` 是所有车型/任务共用的项目根，不能每次换一个根导致备份累积。`-ToolsRoot` 可指定独立工具安装目录；缺省为当前用户的本地应用数据目录下 `ForzaLiveryAgent/tools`。缺省项目根为文档目录下 `ForzaLiveryProjects`。

`-ExecutionPolicy Bypass` 只作用于本次脚本子进程，不修改系统/用户的持久执行策略；受强制策略限制时明确报错。

安装会核对 `toolchain.lock.json` 的下载SHA-256，建立独立 Python 环境，安装本库固定依赖，获取 FLS 1.3.0/FH6Preview/拟合器并生成 `.local/installation.json`。不启动GUI、不修改关联，不写实际游戏存档或Custom。自动查找 Steam 多库及 XboxGames；无法唯一确定时输出候选并保留已装工具，Agent再询问用户资源位置。

指定位置可重跑（已有已校验工具复用）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1 -Workspace C:\LiveryProjects -GameContent 'X:\Games\Forza Horizon 6\Content'
```

读 `.local/bootstrap-result.json` 和 profile，以其中的 `runtimePython` 执行后续脚本。不要沿用别人的绝对路径。图片生成工具由 Agent 当前环境提供，不由此安装脚本创建。

## Agent：开始设计

```text
<runtimePython> scripts/preflight.py
<runtimePython> scripts/workspace.py cars "Nissan GT-R"
<runtimePython> scripts/workspace.py init --name "Project-V1" --theme "用户指定主题" --car-id <核对的ID>
```

私有任务中有 sources/concepts/masters/masks/fits/versions/qa/delivery/logs 和 brief.json。预算预留只是可改默认值，须按用户要求和真实区域规划。确认年份/FE、套件和用户要求，先给实际生图预览，不直接拟合未经核对的角色。

## Agent：工具入口

|阶段|入口|要点|
|---|---|---|
|原生区域|`geometry.py masks --car-id ... --output ...`|读取本车原始遮罩、XML和诊断图|
|实际网格|`geometry.py capture --input ... --output ...`|只观察自己启动的离屏renderer，不附加用户游戏/编辑器|
|世界坐标场|`geometry.py fields --geometry ... --meshes ... --face Left --output ...`|用于跨面/窗同源采样；看几何手册的残差和可见性约束|
|拟合|`livery.py fit <spec.json>`|实际RGBA母稿、前景/权重、预算/保护层、冻结/种子等|
|二维检查|`livery.py inspect/render`|原生图层、预算和真实渲染，不拿假定底画布冒充已输出层|
|整车组装|`livery.py assemble <spec.json>`|每面独立组、余量和实际漆面设置|
|实际上车|`preview.py --exe ... --input ... --game ... --output ...`|新输出目录，验证manifest后真正看PNG|
|小贴纸库|`custom.py --jobs ... --pid ... --output ... [--apply]`|实际用户FLS上下文、按ID保留/精确替换，不关闭编辑窗口|
|原生导出|`native.py export --input ... --seed-header ... --output ...`|用户自己的合法私人身份；合成测试身份禁止用于真实存档|
|本地导入|`native.py install --ready ... --output ... --project-root ... --authorized-note ...`|已授权、游戏关闭、先备份/全量核验、成功后轮转|
|原生工具|`workbench.py --help`|随附Workbench CLI；不依赖旧版内附FLS|
|缓存清理|`cleanup_fit.py --plan <fit>/cleanup-plan.json [--apply]`|确认验收、进程结束后，只删清单内可再生缓冲|

各脚本的 `--profile` 在子命令前传入；默认读取 `.local/installation.json`，也可用 `LIVERY_PROFILE`。preview包装器使用独立 `--exe/--game` 参数。详细参数及流程见根 `SKILL.md` 与 references。

## 用户最终应用

用户可先微调独立小贴纸，再交完整 `.3so` 给Agent导入。本地导入前游戏须关闭；没有本人的可用身份header时，先在游戏中保存一份自己的私人整车草稿，供工具读取合法身份种子。

导入后用户进游戏应用该涂装，进入涂装页保存，按需要发布和下载核查。线上分类、名称和发布由用户决定；本地写入回执不能称为已经在线共享。

## 开发与复现

Windows可加 `-Dev` 安装测试依赖。Linux/macOS可用系统C++17编译器从源码构建拟合器，并运行 `bootstrap.py --synthetic-only --optimizer <编译产物> --uv <uv> --tools-root ... --workspace ... --dev`；这仅验证二维和隔离适配，不表示Windows预览器能在该平台运行。所有测试仅使用合成资料。

发布包附拟合器对应源码；FLS/FH6Preview使用固定上游发行。断网可复用已校验安装，首次在线下载失败会明确报错；不从未知网盘或未核验新版本静默替代。
