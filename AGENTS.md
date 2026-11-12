# CodexMicro-GOWUJI 接力记录

- 目标：低成本复刻 Codex Micro 的实用功能，交付 KiCad PCB/原理图、3D 打印文件、代码、烧录固件、BOM；GitHub Release 包含代码和固件。
- 每轮结束更新本文件。远程仓库 `https://github.com/295173098/CodexMicro-GOWUJI`。提交本地工作可以进行；必须在本轮及后续轮次取得用户明确同意后才可推送、创建远程标签或 GitHub Release。
- 2026-11-13（第 1 轮）：本地分支 `codex/rev-a` 已完成 Rev A Alpha 文件：KiCad 9 原理图与已布线的 95×98 mm 双层板、Gerber/PTH/NPTH、BOM、5 个 STL 及 STEP、ESP32-S3-Zero 固件与合并烧录镜像、Codex App Server 伴侣。预计 ¥55–144/套，不含运费、贴装、人工及外置电源。蓝牙为外部供电的 BLE HID；状态回传走 USB。原厂设备识别与桌面其他会话的实时同步未实现。
- 本轮检查：ERC、DRC、PCB 对原理图校验均为零问题；五份 STL 网格闭合；固件编译通过；本机 Codex App Server 初始化及主机协议检查通过。尚未做样机、烧录实测、蓝牙配对、语音和主机全链路。详见 `docs/validation.md`。
- 本地 Release 审阅件位置：`release/v0.1.0-alpha.1/`；生成方式：`python tools/build_firmware.py`、`python tools/export_hardware.py`、提交源码后 `python tools/package_release.py`。`docs/release-notes.md` 是发布页正文。目标远程在本轮只读检查时为空；未推送、未创建远程 Release。下一步等用户明确批准发布指定版本，或先按 `docs/assembly.md` 验证首件。
