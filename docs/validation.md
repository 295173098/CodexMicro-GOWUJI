# Rev A4 投产前验证

2026-11-13：**可做工程样机，量产暂不放行。** 下面是设计检查、仿真和软件测试结果；尚无实物数据。

| 项目 | Rev A4 结果 |
| --- | --- |
| KiCad 9.0.8 | ERC 0 条；DRC 0 条、未连接 0 处、原理图与 PCB 不一致 0 处。已导出 Gerber 和分开的 PTH / NPTH 钻孔。 |
| 按键拓扑 | 从真实原理图网表穷举 19 个输入的 524,288 种组合、2,097,152 次行扫描，未出现鬼键或漏键。 |
| 按键模拟电平 | 两版合计 64 个模型工况；A4 最差低、高电平分别还有 0.403 V、0.519 V 余量；A1 高电平最差差 0.967 V。A4 保留 BAT46W 和外部 22 kΩ 上拉。 |
| USB 插入浪涌 | 每版 129 个 ngspice 电源工况；接入电荷 A1 为 114.0–364.9 µC，A4 为 38.5–96.6 µC。A4 标称 57.4 µC；最差超过 50 µC 工程参考线，VBUS 过冲模型最高约 6.02 V。 |
| LED 供电 | 保留 TPS22918 软启动和加宽电源走线。LED 铜路回路最差估计为 0.484 Ω，仿真取 0.50 Ω。保守将麦克风旁路的 1.1 µF 折算到 VBUS，并计入 2 mA 录音负载。LED 电源最低 4.357 V，工作总电流峰值约 454 mA。 |
| 机械 | 13 个轴孔和原厂键位排列通过几何检查；2U 键帽在 4.0 mm 设计行程下不碰面板，距右邻键帽约 1.18 mm。USB 开口最小塑料厚度为 1.80 mm（两边各偏 0.20 mm 后剩 1.40 mm），USB 盖与首排键帽相隔约 1.95 mm，板底最小余量 0.45 mm（排针尾脚 ≤3.0 mm）。8 个 STL 网格均闭合。 |
| 板载麦克风 | 网表核对了 3.3 V 供电、L/R 接地、两颗去耦、GPIO3 时钟与 GPIO43 数据串阻；机械模型通过 Ø1.6 mm 通孔、器件避让及 0.60 mm 名义密封间隙检查。PDM 时钟设计值为 2.048 MHz。 |
| 固件与伴侣 | ESP32 Arduino Core 3.3.7 + Adafruit NeoPixel 1.15.2 编译通过。真实固件源码的主机模拟通过键盘回归、双触点 PTT、USB 音频分帧、松键、USB 断线、传输阻塞停止采样及 BLE 禁止录音检查。伴侣测试覆盖无按键开始事件时忽略音频、坏包及跳帧处理。 |

USB 模型扫描电压、线缆电阻和电感、有效电容、开关上升时间、灯电流；芯片软启动与负载均为简化模型。接入电荷取前 1.5 ms 内扣除模块基线后的正向积分，50 µC 仅用作工程参考。Waveshare 模块本身直接接 VBUS 的电容按原理图标称合计 12.3 µF，不能仅凭灯组软启动判断 USB 合规。模型过冲已触及 [TPS22918 数据表](https://www.ti.com/lit/ds/symlink/tps22918.pdf) 6 V 绝对最大额定值；量产前须实测并留裕量。模型未覆盖电磁兼容、静电、实际接触反弹、主机限流细节、射频及 USB 信号质量。

首件放行（建议 3–5 套，每项保留板号、元件批次、测试配置和结果）：

1. 按 [打样与装配](assembly.md) 检查短路、极性和开孔。用实物轴、短尾排针及常用 USB-C 插头干装，确认从 2U 键两端和中间按压都不夹滞，旋钮与摇杆活动正常，导光件和触摸铜箔定位正确。实际透光和串光要装上选定的键帽后逐槽观察，几何及电路仿真未覆盖光学亮度。
2. 在 4.75–5.25 V、短线/长线、USB-A 转 C 和 C 转 C、带限流的集线器上分别进行冷启动和重复热插拔。用示波器记录 VBUS、LED 电源、电流和复位；按 [USB-IF 电气测试方法](https://www.usb.org/sites/default/files/USB%202%200%20Electrical%20Compliance%20Specification%28v1.07%29.pdf) 评估浪涌。确认不过压、不掉电、不触发端口保护，USB 配置前电流符合适用限制（项目参考 100 mA）、配置后 ≤500 mA，并检查 USB 挂起电流及唤醒行为。任一工况不满足就修版并重测。
3. 实测 13 个键、方向、旋钮、触摸及 6 灯满负载，检查 Windows/macOS 的 USB HID/CDC、BLE 配对与重连，以及主机端语音、状态和审批同步。记录长时运行、反复插拔及整机 ESD 结果；依据销售地区核对适用合规要求。
4. 先裸板确认冷启动、复位及烧录都正常；在 USB 模式下测 U4 的 3.3 V 和时钟，确认 2.048 MHz、占空比 40–60%、DOUT 在正确半周期稳定，空闲时无时钟。装壳后用目标距离及多种音量试录，比较开关 RGB 灯和边操作边说话时的底噪、音量和识别效果；检查 60 秒停止、拔线及停止伴侣后均不继续采样。模型没有覆盖实际拾音质量、PDM 串扰、装配气密和 Vosk 的识别率。

复现（PowerShell，`kicad-python.exe` 处替换为能导入 `pcbnew` 的 KiCad Python；仿真需 NumPy，绘图需 Matplotlib）：

```powershell
kicad-cli sch export netlist --format kicadxml --output build/a4.xml hardware/Gowuji-RevA.kicad_sch
kicad-python.exe tools/pcb_metrics.py hardware/Gowuji-RevA.kicad_pcb --out build/simulation/pcb-metrics.json
python tools/simulate_preproduction.py --ngspice 'C:/path/to/ngspice.dll' --netlist build/a4.xml --pcb-metrics build/simulation/pcb-metrics.json --plot
python tools/export_hardware.py --render
g++ -std=c++14 -Wall -Wextra -Werror -I firmware/Gowuji -I tests/firmware tests/firmware/smoke.cpp -o build/sim-fw.exe
build/sim-fw.exe
build/sim-fw.exe ble
python -m unittest discover -s tests -p test_voice.py
```

本地审阅包 `GOWUJI-v0.1.0-alpha.4-review.zip` 包含电路模型、原始结果、波形图、带外壳及电路板 KiCad 3D 图、DRC/ERC 报告。
