# Rev A 验证记录

2026-11-13，软件及设计文件检查通过，尚未制作或烧录实体板。

| 检查 | 结果 |
| --- | --- |
| KiCad 9.0.8 原理图 ERC | 0 条违规 |
| KiCad 9.0.8 PCB DRC 和原理图比对 | 0 条违规，0 处未连接，0 处不一致 |
| Gerber / Excellon | 已导出铜层、阻焊、丝印、钢网、外形及分开的 PTH / NPTH 钻孔 |
| CadQuery / STL | 5 个 STL 的网格全部闭合；底壳和面板外形 99.8 × 102.8 mm |
| 固件 | ESP32 Arduino Core 3.3.7 + Adafruit NeoPixel 1.15.2 编译通过；镜像为 ESP32-S3 |
| 主机 | Python 语法和 USB 消息、配置层、状态映射检查；本机 Codex CLI 0.117.0 App Server 初始化成功 |

首件优先验证 MX 插孔及卡扣、编码器固定脚、摇杆帽公差和实际方向、导光效果、触摸阈值和 USB-C 插头包胶间隙。随后验证 USB、BLE 配对和重连、Codex 回合及审批同步、语音识别。尚未做物理装配、插拔、EMC、Mac 实机或持续运行验证。请按 [首件步骤](assembly.md) 逐项记录。

以发布包的 `*-review.zip` 查看 PCB、原理图和 DRC/ERC 报告；以 Gerber ZIP 打样。当前分支的脚本可重跑相同的检查与导出。
