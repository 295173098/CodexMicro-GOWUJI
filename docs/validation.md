# Rev A3 投产前验证

2026-11-13：**可做工程样机，量产暂不放行。** 下面是设计检查、仿真和软件测试结果；尚无实物数据。

| 项目 | Rev A3 结果 |
| --- | --- |
| KiCad 9.0.8 | ERC 0 条；DRC 0 条、未连接 0 处、原理图与 PCB 不一致 0 处。已导出 Gerber 和分开的 PTH / NPTH 钻孔。 |
| 按键拓扑 | 从真实原理图网表穷举 19 个输入的 524,288 种组合、2,097,152 次行扫描，未出现鬼键或漏键。 |
| 按键模拟电平 | 两版合计 64 个模型工况；A3 最差低、高电平分别还有 0.403 V、0.519 V 余量；A1 高电平最差差 0.967 V。A3 保留 BAT46W 和外部 22 kΩ 上拉。 |
| USB 插入浪涌 | 每版 129 个 ngspice 电源工况；接入电荷 A1 为 114.0–364.9 µC，A3 为 33.3–89.8 µC。A3 标称 52.0 µC；最差仍超过 50 µC 工程参考线，VBUS 过冲模型最高约 6.01 V。 |
| LED 供电 | 保留 TPS22918 软启动及加宽电源走线。按 A3 布线估计最差 LED 铜路回路 0.484 Ω，仿真取 0.50 Ω；LED 电源最低 4.358 V，工作总电流模型峰值约 452 mA。 |
| 机械 | 13 个轴孔和原厂键位排列通过几何检查；2U 键帽在 4.0 mm 设计行程下不碰面板，距右邻键帽约 1.18 mm。USB 开口最小塑料厚度为 1.80 mm（两边各偏 0.20 mm 后剩 1.40 mm），USB 盖与首排键帽相隔约 1.95 mm，板底最小余量 0.45 mm（排针尾脚 ≤3.0 mm）。8 个 STL 网格均闭合。 |
| 固件与伴侣 | ESP32 Arduino Core 3.3.7 + Adafruit NeoPixel 1.15.2 编译通过。主机模拟用真实固件源码测试组合键、防抖、旋钮两方向、触摸、LED 消息、USB 断开、BLE 模式选择和断开，并确认双轴长键只报告一次按下/松开。 |

USB 模型扫描电压、线缆电阻和电感、有效电容、开关上升时间、灯电流；芯片软启动与负载均为简化模型。接入电荷取前 1.5 ms 内扣除模块基线后的正向积分，50 µC 仅用作工程参考。Waveshare 模块本身直接接 VBUS 的电容按原理图标称合计 12.3 µF，不能仅凭灯组软启动判断 USB 合规。模型过冲已触及 [TPS22918 数据表](https://www.ti.com/lit/ds/symlink/tps22918.pdf) 6 V 绝对最大额定值；量产前须实测并留裕量。模型未覆盖电磁兼容、静电、实际接触反弹、主机限流细节、射频及 USB 信号质量。

首件放行（建议 3–5 套，每项保留板号、元件批次、测试配置和结果）：

1. 按 [打样与装配](assembly.md) 检查短路、极性和开孔。用实物轴、短尾排针及常用 USB-C 插头干装，确认从 2U 键两端和中间按压都不夹滞，旋钮与摇杆活动正常，导光件和触摸铜箔定位正确。实际透光和串光要装上选定的键帽后逐槽观察，几何及电路仿真未覆盖光学亮度。
2. 在 4.75–5.25 V、短线/长线、USB-A 转 C 和 C 转 C、带限流的集线器上分别进行冷启动和重复热插拔。用示波器记录 VBUS、LED 电源、电流和复位；按 [USB-IF 电气测试方法](https://www.usb.org/sites/default/files/USB%202%200%20Electrical%20Compliance%20Specification%28v1.07%29.pdf) 评估浪涌。确认不过压、不掉电、不触发端口保护，USB 配置前电流符合适用限制（项目参考 100 mA）、配置后 ≤500 mA，并检查 USB 挂起电流及唤醒行为。任一工况不满足就修版并重测。
3. 实测 13 个键、方向、旋钮、触摸及 6 灯满负载，检查 Windows/macOS 的 USB HID/CDC、BLE 配对与重连，以及主机端语音、状态和审批同步。记录长时运行、反复插拔及整机 ESD 结果；依据销售地区核对适用合规要求。

复现（PowerShell，`kicad-python.exe` 处替换为能导入 `pcbnew` 的 KiCad Python；仿真需 NumPy，绘图需 Matplotlib）：

```powershell
kicad-cli sch export netlist --format kicadxml --output build/a3.xml hardware/Gowuji-RevA.kicad_sch
kicad-python.exe tools/pcb_metrics.py hardware/Gowuji-RevA.kicad_pcb --out build/simulation/pcb-metrics.json
python tools/simulate_preproduction.py --ngspice 'C:/path/to/ngspice.dll' --netlist build/a3.xml --pcb-metrics build/simulation/pcb-metrics.json --plot
python tools/export_hardware.py --render
g++ -std=c++14 -Wall -Wextra -Werror -I firmware/Gowuji -I tests/firmware tests/firmware/smoke.cpp -o build/sim-fw.exe
build/sim-fw.exe
build/sim-fw.exe ble
```

本地审阅包 `GOWUJI-v0.1.0-alpha.3-review.zip` 包含电路模型、原始结果、波形图、带外壳及电路板 KiCad 3D 图、DRC/ERC 报告。
