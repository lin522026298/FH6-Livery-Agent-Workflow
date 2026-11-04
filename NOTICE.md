# 来源与分发说明

本技能的流程文字和适配脚本来自本项目的实际FH6涂装制作与修订经验。

- 基本模板目录和模板数据来自 Forza Painter FH6 GPT 分支的本地核对提交 `29a827d503bb9cba4e9aa3eaf873d97b3e6eb240`。保留其MIT许可、GPT Edition许可及custom importer许可于 `licenses/`。
- 原生基本形状几何和material hash定义对应 ForzaLiveryStudio 生态；图层编码适配参考其livery codec，随本包采用AGPL-3.0，见LICENSE。只保留当前基本模板用到的小型技术数据，未打包游戏车模、纹理或角色原图。
- `native_encoder.py` 由本项目先前验证的source-less编码实现解耦而来；`optimizer_seed.cpp`为本项目的加权/种子优化实现；`capture_native.js`和用户上下文桥为本项目限定用途适配。
- Workbench通用Python源码模块随附在 `vendor/workbench-src`，基于本地基线 `35fdc34ba5a5bcb05a38fdedd68e49cb1d7f8fed`，包含本项目0.2.1滚动备份/读回更新；并非未经修改的该提交，保留AGPL-3.0及第三方说明；未附用户数据。
- FH6Preview、FLS、Workbench完整运行依赖及Frida等按各自许可证安装和使用；本技能不把这些软件的二进制、游戏资源、用户身份或美术作品并入公开技能包。实际本机适配器与版本哈希另存私有清单。

这是一套供AI执行的工作流和脚本，不包含生图服务、游戏、模型服务订阅或适用于所有机器的已配置环境。独立试验状态与证据随发布候选单独列出，不能以本文件代替验收。

公开发布新增跨设备安装、Agent入口、独立环境与游戏路径发现。工具链下载固定版本与SHA-256；不重新许可第三方组件。FH6Preview包装脚本来自 https://github.com/lin522026298/FH6-Background-Preview ，遵循AGPL-3.0。
