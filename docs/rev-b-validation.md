# Rev B 工程打样状态 · 2026-11-16

**可提交 3–5 套 PCBA 工程样机的报价/CAM 审核；工厂回签后再开工，量产未放行。** 当前交付入口是[打样下单说明](rev-b-order.md)，本地完整包 `build/rev-b-pcba.zip`。本轮未上传、下单或远程发布。尚无工厂 CAM、供料与旋转回签，不能称为工厂已批准。

- KiCad 9.0.8 重新检查：ERC 0、DRC 0、未连接 0、原理图一致性差异 0。1,657 段走线、164 个过孔、4 个铜区及 3 个规则区。补齐了项目的三个标准封装库引用，解决新电脑缺库警告；铜几何未改。
- 网表 524,288 个键态通过。独立 Gerber 解析确认四铜层、202 个 PTH 和 45 个 NPTH；单独分离镀槽。最细走线实际为 0.10 mm（扇出），不是 0.14 mm；后者是局部间距规则。
- 采购表按位号完整覆盖 105 个封装，输出 78 SMT + 1 USB 混装点位、14 个后焊点位；C19/C20 不贴。补齐指定电阻、电容、晶振及极性图，见[元件审核](rev-b-component-review.md)。尚未锁定供货库存或价格。
- 电容偏压纳入模型：C10 1–2.8 µF、C14 2–6 µF、C15 10–28 µF、LED 总容量 12–62 µF。1,728 个热插拔工况板内峰值 5.25 V、插座端 6.20 V、前 100 µs 电荷 46.17 µC；R16/R17 最大脉冲分别 16.01/6.69 W，按所选厂商曲线的保守界限初筛通过。
- 1,024 个启动/带载角点：正常 USB/BLE 预算峰值约 402/472 mA；芯片最低约 3.217/3.207 V。无约束 BLE 压力达 582 mA，不属于正常预算。
- **枚举前/挂起未获验证**：简化启动模型可出现约 110 mA，不能宣称满足枚举前 100 mA 限制；还要实测并视结果改启动/使能。它和真实热插拔、温升、USB 正反插、PDM、RF、外壳配合均列入首件验收。
- PCB 控制阻抗指定 JLC04161H-3313；2D 设计估计 USB 89.99 Ω、RF 49.92 Ω，必须由工厂用实际工艺确认。QFN 散热孔填孔/封帽或替代塞孔钢网方案、工艺边及旋转需工厂回签。

以下保留上轮数据作追溯，数字和“不可下单”状态不能覆盖本轮结论；也不能跳过上方仍需工厂确认的条件。

---

# 2026-11-14 历史审阅记录（已由上方 2026-11-16 状态替代）

2026-11-14 · **PCB 不可下单打样，也不可试产**。本记录针对 `hardware/rev-b` 的板载 ESP32-S3 版。A4 的板和仿真数据不能用于 Rev B。

| 检查 | 核对或仿真结果 |
| --- | --- |
| KiCad 原理图 ERC | 0 项违规 |
| KiCad PCB DRC 与原理图一致性 | **0 项未连接**（原摆件板 210 项）、0 项其他规则违规、0 项原理图一致性差异。1,657 段走线、164 个过孔、4 个接地覆铜区。 |
| 原理图网表 | USB-C 两个插入方向的 D+/D−、两路独立 CC 下拉、VBUS、3.3 V 和板载麦克风 PDM 连接核对通过。19 个触点的 524,288 种开合组合全部比对正确，模型未见鬼键或漏键。 |
| USB 输入阻尼（已上板） | R16 为 0.82 Ω 公共串阻，R17 为 C14 支路的 1.5 Ω 阻尼；C10 改 2.2 µF 并保持直连。旧版无阻尼在扩展模型中峰值达 9.55 V；旧版双支路阻尼方案只作对照，不用于此板。 |
| ngspice：当前板热插拔模型 | 1,728 组角点：板内 VBUS 峰值 5.25 V，插座侧 VBUS_RAW 6.20 V；输入网络前 100 µs 接入电荷最大 41.2 µC。R16 最大脉冲电流 4.50 A、最大单次脉冲能量 64.7 µJ，来自不同工况。 |
| ngspice：带载和启动模型 | 512 组简化仿真。常规 USB 峰值 400.3 mA，ESP32 最低 3.217 V、末颗灯 4.127 V；按 0 dBm 供电预算的 BLE 工况峰值 469.8 mA，以上最低电压为 3.207 V、4.034 V。不限制 BLE 的压力工况达 578.7 mA。500 mA 单独稳压器压力工况中，ESP32 最低 3.172 V。 |
| Rev B 固件 | 使用 ESP32 Arduino 3.3.7、4 MB Flash 和 QSPI PSRAM 编译通过。BLE 广播及默认发射功率请求 0 dBm；控制器拒绝时不启动广播。已生成 `build/firmware-rev-b/Gowuji.ino.merged.bin`；实际发射功率、烧录与启动待样机。 |

R16 之前的 VBUS_RAW 仅接插座，稳压器、USB ESD 阵列供电端和 [TPS22918](https://www.ti.com/lit/ds/symlink/tps22918.pdf) 均接 R16 之后的 VBUS；6 V 绝对最大值对照的是后者。C10 应选在 5.25 V 和容差下仍至少 1 µF 的料号；R16/R17 应按实际脉冲曲线选型。热插拔模型未计入主机限流、PCB 寄生和接触反弹。带载使用行为模型，没有验证 USB 枚举前与挂起的电流、实际稳压器上电、LED 最低电压下的数据阈值或装壳温升。两颗阻尼电阻在底壳 CAD 中有额外 0.5 mm 垂直余量。

可继续核对的料号：R16 [Panasonic ERJ8BQFR82V](https://industrial.panasonic.com/ww/products/pt/current-sensing-chip-resistors/models/ERJ8BQFR82V) 满足 1206、0.82 Ω、0.5 W、±1% 的静态规格，尚未确认其重复脉冲能力；C10 Murata GRM188Z71E225KE43 是 0603、2.2 µF、25 V、±10% X7R，尚需用厂商直流偏压数据确认有效电容。

首轮将 USB 数据主段、40 MHz 晶振和射频匹配走在顶层，`In1.Cu` 保持为地参考；VBUS 用 0.50 mm 内层主干，LDO 移到底面以避开 USB 走线。底壳 CAD 检查显示 LDO 包络和额外 0.5 mm 的垂直余量无干涉；还需复核温升、贴装和整机公差。ESP32 的 CPU 3.3 V（46）和 PDM 数据（49）已接通。西、南、北三处扇出采用 0.40 mm 焊环外径、0.20 mm 钻孔；自定义规则将这两项尺寸和顶层 0.14 mm 走线间距限制在扇出区内，其它位置沿用常规参数。下单时需确认板厂支持这些尺寸，可参考 [嘉立创四层板工艺能力](https://jlcpcb.com/capabilities/Capabilities)。阻抗目标为 USB 90 Ω 差分、射频 50 Ω，当前走线尺寸须按板厂叠层调整并验证。手工关键网络的初始走线由 `tools/route_rev_b.py` 生成；该脚本接收未布线的摆件板，以 KiCad 主板文件的最新走线为准。

1. **下单前**：确定板厂四层叠层和实际料号，确认 USB 90 Ω 差分、射频 50 Ω 及连续地回流、晶振、QFN 裸露焊盘和 LDO 散热；复算输入保护、浪涌电荷、3.3 V 上电与 BLE 和灯负载引起的压降，确认供电预算。ERC、DRC（含未连接）及一致性通过后，再核对 Gerber、钻孔、贴装坐标、BOM 版本和烧录镜像。
2. **首批工程样机**：前述项目通过后先做 3–5 套。示波器测 USB 热插拔峰值与电荷、3.3 V 启动和峰值负载下跌落，测 LDO 温升，并检查 USB-C 正反插枚举和烧录、BLE、麦克风与壳体配合。
3. **小批试产**：首批实测通过、问题关闭后再安排。当前可以独立 3D 打印外壳，用现成轴和 USB 插头做配合验证。

制造审阅文件在 `build/rev-b-fab-review/`，包含四层 Gerber、双面钢网层和贴装坐标，以及分开的 PTH/NPTH 钻孔。钻孔报告列出 202 个镀孔（15 个标称 0.20 mm）和 45 个非镀孔。坐标导出包含带通孔外壳的 J2，交给贴装厂前按工艺分类并核对旋转。板厂参数见[制造审阅单](rev-b-fab-notes.md)。审阅件不可下单。

已把 [嘉立创 JLC04161H-3313 叠层](https://jlcpcb.com/impedance)写入 KiCad：1.6 mm，外层铜 35 µm，外层到邻近参考层标称 0.0994 mm，ENIG。USB 插座的 A/B 并线全部改到顶层，撤掉四个信号过孔并缩短 D+ 串阻前走线。插座至 MCU 的几何路径差由约 7.39/4.12 mm 降到 5.77/3.48 mm；用于比较布线，不等同于时延测量。提取填铜后确认铜覆盖了两组插座并线、USB 平行主段和两段射频干线的全线宽。射频主段从 0.28 mm 改为 0.16 mm，保留器件过渡。

用 `tools/rev_b_impedance.py` 做二维准静态计算，包含梯形铜、阻焊和同层地：USB 0.18/0.27 mm 直线段约 90 Ω，射频 0.16 mm 主段约 50 Ω（改前约 37 Ω）。此模型不包含器件、局部不连续、纵向长度或板厂的压合和蚀刻公差。下单前仍需板厂用实际叠层复核，首批用阻抗券与 USB 双向枚举验证。

```powershell
New-Item -ItemType Directory -Force build/rev-b-validation | Out-Null
$board = "hardware/rev-b/Gowuji-RevB"
& .local/kicad/bin/kicad-cli.exe sch erc --format json --exit-code-violations -o build/rev-b-validation/erc.json "$board.kicad_sch"
& .local/kicad/bin/kicad-cli.exe pcb drc --schematic-parity --format json --exit-code-violations -o build/rev-b-validation/drc.json "$board.kicad_pcb"
& .local/kicad/bin/kicad-cli.exe sch export netlist --format kicadxml -o build/rev-b-validation/netlist.xml "$board.kicad_sch"
python tools/simulate_rev_b.py --netlist build/rev-b-validation/netlist.xml --out build/rev-b-validation
python tools/simulate_rev_b_power.py --ngspice .local/kicad/bin/ngspice.dll --out build/rev-b-power/dynamic
python tools/rev_b_impedance.py --width 0.18 --spacing 0.27 --gap 0.22 --step 0.0025
python tools/rev_b_impedance.py --width 0.16 --gap 0.22 --step 0.0025
./tools/export_rev_b_review.ps1 -KiCadCli .local/kicad/bin/kicad-cli.exe
```
