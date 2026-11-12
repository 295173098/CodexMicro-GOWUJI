# CodexMicro-GOWUJI 接力记录

- 目标：低成本复刻 Codex Micro 的实用功能，交付 KiCad PCB/原理图、3D 打印文件、代码、烧录固件、BOM；GitHub Release 包含代码和固件。
- 每轮结束更新本文件。远程仓库 `https://github.com/295173098/CodexMicro-GOWUJI`。提交本地工作可以进行；必须在本轮及后续轮次取得用户明确同意后才可推送、创建远程标签或 GitHub Release。
- 2026-11-13（第 1 轮）：本地分支 `codex/rev-a` 已完成 Rev A Alpha 文件：KiCad 9 原理图与已布线的 95×98 mm 双层板、Gerber/PTH/NPTH、BOM、5 个 STL 及 STEP、ESP32-S3-Zero 固件与合并烧录镜像、Codex App Server 伴侣。预计 ¥55–144/套，不含运费、贴装、人工及外置电源。蓝牙为外部供电的 BLE HID；状态回传走 USB。原厂设备识别与桌面其他会话的实时同步未实现。
- 本轮检查：ERC、DRC、PCB 对原理图校验均为零问题；五份 STL 网格闭合；固件编译通过；本机 Codex App Server 初始化及主机协议检查通过。尚未做样机、烧录实测、蓝牙配对、语音和主机全链路。详见 `docs/validation.md`。
- 本地 Release 审阅件位置：`release/v0.1.0-alpha.1/`；生成方式：`python tools/build_firmware.py`、`python tools/export_hardware.py`、提交源码后 `python tools/package_release.py`。`docs/release-notes.md` 是发布页正文。目标远程在本轮只读检查时为空；未推送、未创建远程 Release。下一步等用户明确批准发布指定版本，或先按 `docs/assembly.md` 验证首件。

- 2026-11-13（第 2 轮，仿真与 3D 查看）：`codex/rev-a` 更新到 Rev A2。增加 TPS22918 软启动、22 kΩ 上拉、BAT46W 二极管，加宽电源与地走线，修正 WS2812B-MINI-V6 焊盘和方向。重布线后 ERC、DRC、原理图比对均为 0 问题；13 键面板、底壳和轴孔试片已更新，6 个 STL 闭合。成本估算 ¥58–153/套。
- ngspice 每版 129 组电源工况，A2 浪涌电荷 33.3–89.8 µC（A1 114.0–364.9 µC）；过冲模型最高 6.01 V。网表穷举 524,288 组合无鬼键或漏键；固件 USB/BLE 主机模拟及 ESP32-S3 实际编译均通过。**工程样机可审，量产暂不放行**：按 `docs/validation.md` 实测热插拔、VBUS 过冲、挂起、USB/BLE 和首件装配。
- 在桌面 KiCad 打开并旋转了 Rev A2 3D 查看器。PCB 装配预览有 13 个键帽、旋钮、摇杆、USB 模块与贴片模型；模型简化，外壳另见 `mechanical/fit-reference.step`。渲染图 `build/review/GOWUJI-RevA2-3D.png`，仿真报告 `build/simulation/`。
- 当前本地候选 `release/v0.1.0-alpha.2/`，提交源码后用 `python tools/package_release.py --include-simulation` 打包，含源码、烧录镜像、Gerber 和仿真审阅 ZIP。未推送 GitHub、未创建远程标签或 Release；继续遵守发布前明确同意要求。

- 2026-11-13（第 3 轮，核对原厂按键）：用户指出 KiCad 图上的按键与原厂不同。确认 A2 为压低成本采用通用 MX 直焊轴和无刻字的单宽键帽模型，六个状态键在左侧 2 列 × 3 排，旋钮和摇杆在底排，未按原厂物理布局排布。原厂上方为六个磨砂透光状态键（第一排中间 2 个、第二排 4 个），旋钮和摇杆在左右上角，底部有 2U 宽键。参考 [OpenAI 产品页](https://openai.com/zh-Hans-CN/supply/co-lab/work-louder/)、[Work Louder 使用说明](https://www.worklouder.cc/setup/codex-micro) 和 [实物键位测绘](https://arthurcolle.github.io/codex-micro-open/#discovery-2-the-keycaps-hide-thirteen-switches)。后续按原厂外观修版时，先对齐键位、透光方式和面板，再验证标准低价轴与键帽兼容性，重跑 PCB 和装配检查。本轮仅核对和记录，Rev A2 硬件及本地打样包未改，未上传 GitHub。

- 2026-11-13（第 4 轮，用户要求对齐原厂）：Rev A3 已将旋钮放左上、摇杆放右上、六状态键放上两排、触摸放左下、双轴 2U 语音键放底排。更新 95×98 mm 双层 PCB、原理图、BOM、外壳、面板和器件模型，提供可打印 2U 键帽及可拆 USB 盖。保留通用 MX 直焊轴与 A2 软启动，预计 ¥60–159/套。两个长键触点聚合为一个 PTT 动作，切层由触摸片完成；并非复制原厂材料、手感、通信或授权软件集成。
- A3 KiCad ERC/DRC/一致性各 0，网表穷举 524,288 组合无鬼键或漏键，主机 USB/BLE 固件测试及 ESP32-S3 编译通过。ngspice 浪涌 33.3–89.8 µC，过冲模型最高 6.01 V。机械几何和 8 个 STL 网格检查通过；首件须验证 2U 偏心按压、导光及 USB 热插拔和挂起。仍只允许工程打样，量产暂不放行。
- 本地打样候选 `release/v0.1.0-alpha.3/`，源码、镜像、Gerber、报告齐备；带壳渲染 `build/review/GOWUJI-RevA3-assembled.png`。新一版用 `python tools/export_hardware.py --render` 导出，先按 `docs/validation.md` 完成仿真。A2 备份候选仍在旧目录，A2/A3 PCB 与外壳不能混用。未上传 GitHub、未发布 Release；任何远程发布仍需明确许可。
