# Rev B 工程样机元件审核（2026-11-16）

采购以 `hardware/rev-b/assembly-parts.csv` 为准，按位号覆盖 PCB 全部 105 个封装。旧 `BOM.csv` 的价格区间用于历史估价，不作为自动代料依据。以下核对支持首批工程样机选择，未做实物寿命或合规认证。PCB 铜几何与阻容标称值未因此改变。

## 输入阻尼电阻

R16 锁定 **Bourns CRM1206-FX-R820ELF**，0.82 Ω、±1%、0.5 W；R17 锁定 **Vishay CRCW06031R50FKEAHP**，1.5 Ω、±1%、0.33 W。仿真仍采用更宽的原 ±5% 阻值边界，覆盖这些料号及正常温漂。不能用普通通用贴片电阻按相同阻值代换。

[Bourns CRM 数据表](https://www.bourns.com/docs/product-datasheets/crm0805_1206_2010.pdf) 第 1 页公开脉冲曲线中，CRM1206 在 100 µs 的峰值功率约 150 W；工程初筛保守按 100 W。用整个 100 µs 区间的峰值矩形包络比较，而不是把单次能量除以任意短时间。R16 的直流预算为 0.5 A 时约 0.22 W，低于 0.5 W；实际装壳温度仍须验证。该曲线没有给出本项目接触反弹和重复插拔寿命保证，首件应记录阻值前后变化。

[Vishay CRCW-HP 数据表](https://www.vishay.com/docs/20043/crcwhpe3.pdf) 第 5 页连续脉冲曲线，在 100 µs 处的 0603-HP 允许功率高于 10 W；本次保守按 10 W 比较。除脉冲峰值外，平均功耗须满足温度降额曲线；本电容支路的稳态直流电流近零。用峰值矩形包络时，100 µs 内实际功率均不得超过该界限。原 Panasonic ERJ8BQFR82V 未作为此打样包的已核定脉冲料。

## 电容的有效容量

从[村田 SimSurfing](https://ds.murata.com/simsurfing/mlcc.html)取得所选料号 25 °C 的公开 C–DC bias 数据。下表以相对于零偏压曲线的比例归一到标称容量，再乘 **0.90 容差 × 0.85 温度余量 × 0.90 额外余量**。这是偏保守的设计筛查，仍是典型曲线推算，不是厂商保证的逐颗下限；代料需重做审核。曲线测量 AC 为 C10/C14 1 Vrms、C15/C8 0.5 Vrms，不能把它当作全部小信号条件的保证。

| 位号/锁定料号 | 偏压 | 曲线容量保留比例 | 推算含余量容量 | 仿真范围 |
| --- | --- | --- | --- | --- |
| C10 GRM188Z71E225KE43D，2.2 µF/25 V | 5.25 V | 70.06% | 约 1.06 µF | 1.0–2.8 µF |
| C14 GRM31CR71C475KA01L，4.7 µF/16 V | 5.25 V | 95.42% | 约 3.09 µF | 2.0–6.0 µF |
| C15 GRM31CR71A226KE15L，22 µF/10 V | 3.3 V | 74.85% | 约 11.34 µF | 10–28 µF |
| C8 GRM31CR61A476KE15L，47 µF/10 V | 5.25 V | 35.82% | 约 11.59 µF；另有六颗灯去耦 | LED 总容量 12–62 µF |

原模型把 LED 总电容固定为 45 µF；现扩展为 12/62 µF 两端，共 1,024 个带载工况。热插拔 C10/C14 上限同时扩展以纳入正容差/温度，仍为 1,728 个工况。两类模型分别研究前 100 µs 输入网络、启动与 42 ms 负载脉冲；没有包含真实稳压器环路、主机限流、全部寄生或重复触点反弹。不得把 100 µs 电荷当成整个上电过程的 USB 合规结论。启动模型在 3–20 ms 可出现约 110 mA，因此**未证明枚举前 100 mA 限制满足**；首件必须测，必要时修改 LED 使能/启动安排。

最新扩展仿真结果如下，独立极值可能来自不同角点：

| 检查 | 结果 |
| --- | --- |
| 1,728 个热插拔工况 | 板内 VBUS 最高 5.25 V；插座侧 6.20 V；前 100 µs 最大接入电荷 46.17 µC |
| R16 脉冲 | 最大 4.53 A、16.01 W、70.92 µJ；低于所选曲线的保守 100 W/100 µs 包络 |
| R17 脉冲 | 最大 6.69 W、54.19 µJ；低于所选曲线的保守 10 W/100 µs 包络 |
| USB 指示灯+麦克风（256 组） | 配置后峰值约 402 mA，芯片最低 3.217 V，末灯最低 4.110 V |
| 约束 BLE+灯（256 组） | 配置后峰值约 472 mA，芯片最低 3.207 V，末灯最低 4.011 V |
| 无约束 BLE 压力（256 组） | 峰值约 582 mA，不纳入 500 mA 供电使用预算 |
| 500 mA 稳压器压力（256 组） | 芯片最低约 3.171 V，输入峰值约 512 mA；只作压力试验 |

## 时钟、极性与装配

X1 采用 **ABM8-40.000MHZ-10-D1G-T**，40 MHz 基频，CL 10 pF，±10 ppm 初差、±15 ppm 温稳，3225 四焊盘；[Abracon 官方数据表](https://abracon.com/Resonators/ABM8.pdf)给出 1/3 为晶体端、2/4 接地。C17/C18 为 15 pF C0G 起始值，按板寄生与首件频率测量调整。封装倒角可以在不同角，必须按电气脚号和来料卷带确定旋转。

[WS2812B-MINI-V6](https://www.world-semi.com/downloads/datasheets/en/ws2812b-mini-v6-1.0.pdf) 的四脚顺序与现封装核对一致：1 VDD、2 DOUT、3 GND、4 DIN，标记角是 3 脚。不接受 MINI-X1 代换。[MP34DT06J](https://www.st.com/resource/en/datasheet/mp34dt06j.pdf) 1 VDD、2 LR 接地、3 CLK、4 DOUT、5 外围地环。所有焊盘的实际坐标随包提供。库中的角度零点需由贴装厂结合来料再次确认。

L1 的 2.2 nH 和 C19/C20 DNP 是初始 RF 匹配，配 50 Ω U.FL 天线做工程样机；不宣称已测得输出功率或天线效率。外壳、天线采购和装壳位置不由 SMT BOM 自动完成。

## 复现与证据

```sh
python3 tools/simulate_rev_b.py --netlist build/rev-b-order/netlist.xml --out build/rev-b-order/logic
python3 tools/simulate_rev_b_power.py --ngspice /path/to/libngspice.so.0 --out build/rev-b-order/power-final
python3 tools/rev_b_impedance.py --width 0.18 --spacing 0.27 --gap 0.22 --step 0.0025
python3 tools/rev_b_impedance.py --width 0.16 --gap 0.22 --step 0.0025
```

本轮电源角点 JSON、最差电路及村田请求和响应保存在 `build/rev-b-order/`。模型通过只能支持工程试制，真实 USB 热插拔、枚举前/挂起功耗、PDM、BLE、QFN 焊接、温升和壳体配合继续按首件表验收。工厂未做供料与 CAM 回签前不得直接投产。
