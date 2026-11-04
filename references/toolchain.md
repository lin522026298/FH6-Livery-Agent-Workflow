# 工具、安装与发布边界

## 主线工具与来源

|工具|作用|当前复用方式与边界|
|---|---|---|
|前沿多模态执行模型|理解要求、看图、编排和迭代|本项目推荐GPT-6.1 Sol/max或可比/更强能力；不是跨模型实测排名|
|内置image_gen／精确参考生图器|概念预览、角色与背景母稿、局部修改|独立于语言模型；使用真实参考并实际检查，不以代码图形替代插画；默认无API Key|
|FFmpeg/Pillow、静默视频下载技能、yt-dlp等|GIF选帧、官方PV/技能演示取帧、原始资料收集|按需使用，只读/下载合法可得资料；不启动前台浏览器或播放器，记录源URL与帧时间|
|[Forza Painter FH6 GPT分支](https://github.com/DDDuoDuo/forza-painter-fh6-gpt)|原生模板、图形数据与拟合生态|所核对源提交29a827d；包括原生模板/渐变等；不意味着每个任务都使用GUI或渐变|
|本项目 `optimizer_seed`|加权、严格前景、种子续拟合、冻结前缀、重优化|实际成功方案大量使用的自用C++ **CPU** 拟合器。来源和参数需明确，不冒充官方原版界面；源文件随技能，已验证EXE放本机工具目录|
|本技能 `livery.py/core.py`|预算检查、DAT转原生形状、原生二维渲染、独立组装|不含历史角色素材；只带小型基本模板数据。复杂原生资源仍用完整FLS渲染器|
|[Forza Livery Studio](https://github.com/Arstz/ForzaLiveryStudio) 1.3.0|可编辑工程、用户拼贴、小贴纸库|用户端默认1.3.0；核验实际进程路径；AI生产一般不启动GUI|
|[FH6-Background-Preview](https://github.com/lin522026298/FH6-Background-Preview) / FH6Preview 1.0.0|离屏实际车模、多机位、原生涂装检查|自用后发布的工具；调用现有 `fh6-livery-preview` 技能或隐藏子进程，无系统输入；效果仍为FLS参考渲染|
|本技能 `geometry.py` + 限定Frida观察桥|原始遮罩、UV索引三角形、世界坐标、车窗续贴规划|仅观察自己新建的离屏renderer；不附加游戏；协议与已核对renderer哈希绑定|
|[FH6 Livery Workbench](https://github.com/lin522026298/FH6-Livery-Workbench) 0.3.0|自制作品转换、校验、完整备份、本地导入和读回|无界面CLI与对应源码、模块清单和PowerShell清理助手；项目级滚动留一份、失败/损坏暂停；默认追加，不自行发布|
|本技能 `custom.py` + 用户上下文桥|真实FLS进程中的Custom按ID合并/替换|限定注册表值、备份、CAS与同上下文读回；不关闭编辑器，面板可见由用户重载确认|
|Python、NumPy、Pillow、OpenCV、Frida|可重复图像采样、数据和受限进程接口|独立虚拟环境；记录实际版本。不得把模型生图篡改成纯脚本手绘人物|

可选工具：Vinylizer 1.x/2.x、ForzaSqueegee、SVG/Inkscape相关路线。仅按图案与已验证结果选择，不为了“新版/矢量”强制替换当前有效路径。没有在本次使用或验证的工具不能在报告中写成生产依赖。Itasha分支功能也需具体测试后再记为优势。

## 本机配置与可移植性

GitHub版首选根目录 `bootstrap.ps1` 自动安装并核验固定发行包，私有配置默认写入 `.local/installation.json`（Git忽略）。亦可用 `--profile` 或 `LIVERY_PROFILE` 指向其他私有配置。运行时独立目录由 `-ToolsRoot` 决定，不依赖作者的工具目录。本文其余手动安装方式供开发者/已有工具的高级配置使用。

公开包不包含绝对路径、用户身份、游戏资源、旧素材、备份或API Key。每台电脑建立私有 `installation.json`，可放技能根目录（发布时排除）或用 `--profile` 指定。

配置字段：

- `runtimePython`：本机工具独立虚拟环境解释器。
- `optimizer`、`optimizerSha256`：通过合成测试的自用拟合EXE及哈希。
- `previewExe`、`previewSha256`：FH6Preview与已核对协议版本的哈希。
- `flsExe`、`flsSha256`：用户选定1.3.0安装程序；实际使用还核验进程路径。
- `carsCatalog`：FLS车型ID/模型目录JSON。
- `gameContent`：用户合法游戏Content目录，只读。
- `workbenchSource`：可选，包含 `fh6_livery_workbench/` 的Python源码目录；省略时使用随包的 `vendor/workbench-src`（AGPL-3.0源码与原许可）。
- `backupPolicyRoot`：整套涂装项目的共同根，所有车型/子任务共用滚动完整备份登记；正式导入亦可显式传 `--project-root`。不能绑定每次任务的新输出目录或真实存档根。独立Workbench配置同义字段为 `backup_policy_root`。

运行时工具放独立ToolsRoot，不覆盖Painter/FLS旧安装。bootstrap建立venv、核对过的optimizer及下载的预览器/FLS；Workbench源码随仓库提供，避免指向作者电脑的依赖路径。原安装、游戏和用户素材不随公开包复制。

```text
uv venv <本机工具目录>/.venv
uv pip install --python <本机工具目录>/.venv/Scripts/python.exe -r requirements.txt
python scripts/preflight.py --profile <本机配置> --output <新核验文件.json>
python scripts/self_test.py --profile <本机配置> --output <新的隔离自检目录>
```

`scripts/optimizer_seed.cpp` 是独立标准C++源；有合适编译器时可用 `c++ -O3 -std=c++17 optimizer_seed.cpp -o optimizer_seed.exe` 构建，然后在新目录执行合成测试和原生渲染对比，不能只因编译成功就覆盖生产二进制。预览与FLS依赖遵循各自发行说明。

`self_test.py`只用合成图形和隔离Custom/存档，覆盖预算预留、透明度拒绝、真实拟合、原生导出、旧文件保留、目标冲突拒绝、Custom追加/幂等/精确替换。它不替代真实角色和整车的视觉前向试验。运行时没有真实游戏存档写入，也不宣称已在用户Custom面板显示。

v1.1起自检还执行两次隔离PGS追加：新备份与全量读回完成后才删前次完整ZIP；再触发冲突，核验失败暂停清理并保留两份。Workbench回归测试另覆盖损坏报告、无重复询问、备份损坏、源存档变化、路径越界及清理失败。PyInstaller和Python wheel均须包含 `delete_backup_archives.ps1`，缺少助手时应保留备份并报清理待办，不能悄悄用未验证删除路线。

## 拟合参数文件

`livery.py fit <spec.json>` 的核心字段：`input`（实际RGBA PNG）、`output`（新的目录）、`budget`（含保护层的最终预算）、`name`。

可选：`foregroundMask`（等尺寸8位PNG）、`weights`（等尺寸8/16位灰度PNG）、`maxWeight`、`alphaThreshold`、`seedDat`、`frozenSeedCount`、`protected`（独立原生保护特征.3so）、`baseColor`、`baseAlpha`、`passes`、`recycles`、`timeoutSeconds`、`supersample`。默认严格图案域；真实保护层计入总预算。改变分辨率/裁切时必须转换种子坐标，不能直接沿用旧DAT。

输出保存 `actual-input.png`、域与权重、参数、DAT、原生贴纸`.3so`与渲染、技术回执及缓冲清理清单。拟合技术成功仍需看原生PNG。

`baseColor/baseAlpha`是拟合器假定的底画布，不自动变成DAT图层。车身使用不透明底画布时，组装必须另加同色的一层底色并计入预算；`native.png`只显示真实输出形状，不能把假定底画布当成已输出图形。独立透明贴纸/窗续贴一般使用`baseAlpha=0`，不在整扇窗上加不透明底。

## 组装参数文件

`livery.py assemble <spec.json>`：`carId`、`name`、`output`、`sections`、可选 `creator`、`reserves`、`liveryPaint`。sections以Front/Back/Top/Left/Right/Wing/Glass_*命名，每个值为独立组数组。

一层底色项：`{"name":"统一底色","baseColor":[21,44,52]}`。

图案项：`{"name":"人物与背景","project":"<独立原生.3so>","transform":{"x":0,"y":0,"scale_x":1,"scale_y":1,"rotation":0,"skew":0}}`。

输入贴纸默认以其原图中心为原生原点。将拟合图放到本车某个native矩形时按相同裁切/比例转换；不是把PNG当原生贴在车上。跨窗映射先生成窗专用目标，另行拟合再组装。

新整车会显式物化与原生导出相同的材质默认表和轮毂前后轴fallback。空`.3so`材质表与原生存档里“存在但禁用”的条目，在参考渲染器中可能显示不同的默认轮毂/玻璃；不能只检查图案坐标而忽视此差异。自定义漆面也按导出规则规范化，再进行源工程/原生包的上车对照。用户已有完整漆面配置则保留其明确设置，不擅自换颜色。

新设计时还须主动选定车身漆色，而非只依赖默认表。无特殊要求，车身本体各漆面使用涂装主体色调；玻璃、刹车和轮圈单独处理。依据已核验的原生材质描述表设置 `liveryPaint`，保存色值/材质及适用部件清单，不能凭空编造属性。图层底色与实际车漆分别验证；单纯导入用户既有工程则不套用新设计的换色默认。

`reserves`按面指定用户保留，例如 `{"Left":100,"Right":100,"Top":100,"Glass_Left":600,"Glass_Right":600,"Back":700}`。程序按真实叶子图层计数，不靠metadata旧数值。

## 包的形式

首选 **Agent Skill + 可执行适配脚本 + 详细手册 + 测试证据**。Skill适合AI按自然语言调用；人类手册适合查阅；脚本承载脆弱的坐标、序列化和文件操作。不把所有经验塞进一个长系统提示，也不先做需要前台GUI的新应用。

本轮形成可安装技能ZIP与发布候选源包。公开发布应只含通用代码、文档、模板数据和许可证；排除本机配置、角色图、成品、游戏模型、存档、身份、Custom库和试验私有输入。外部仓库/市场发布另按用户明确指示执行，不能把本地打包称为已公开。

官方机制参考：[Skills](https://developers.openai.com/plugins/concepts/skills)、[技能评估](https://developers.openai.com/blog/eval-skills)。模型设置依据：[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)，其中支持max；“至少该等级”来自本项目经验要求，不是官方最低配置保证。

## 版本兼容

FLS用户项目可能为v4，旧Workbench通用project loader只接受到v3。本技能loader明确接受已知v3/v4结构，导入器独立核验原生数据；不直接调用那个旧loader去读v4。

若旧预览器拒绝v4，只有在确认所用图形、变换、材质和组语义均兼容后，生成**仅预览副本**并证明只变更顶层版本号；原件不动。发现v4新增未知特性时使用新版解码器或明确阻塞，不靠改数字假装兼容。
