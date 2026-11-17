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

- 2026-11-13（第 5 轮，打开 3D）：启动了本机 KiCad PCB 编辑器。Windows 窗口捕获持续报 GPU 设备实例暂停（`0x887A0005`），文件对话框控件重试后也无法验证，未确认 3D 查看器打开。可手动在 KiCad 打开 `build/review/assembly-preview.kicad_pcb` 并按 `Alt+3` 看带外壳整机；静态图为 `build/review/GOWUJI-RevA3-assembled.png`。硬件、打样包及远程状态未改。

- 2026-11-13（第 6 轮，恢复 3D）：用户修复 GPU 后，重置窗口捕获会话并重新启动 KiCad，打开 `build/review/assembly-preview.kicad_pcb`。已确认带外壳的 Rev A3 3D 查看器正常渲染，停在前台斜视角，外壳及新键位完整可见。只更新接力记录，未改设计、打样包或远程仓库。

- 第 7 轮（确认麦克风）：Rev A3 没有板载麦克风，2U 话筒图标键只发送 PTT 控制事件；USB 伴侣使用电脑或外接耳机的麦克风，并在配置本地 Vosk 后将转写填入草稿。仅核对现状，未改硬件、固件或发布包。

- 2026-11-13（第 8 轮，板载麦克风）：Rev A4 增加 U4 MP34DT06JTR（C503097），GPIO3 时钟、GPIO43 数据及串阻/去耦；顶面左上 Ø1.6 mm 拾音孔，使用泡棉环连接面板与麦克风。键位和双层板轮廓沿用 A3，BOM 估算 ¥63–170/套（新增 ¥3–10，不含贴装）。USB 模式需伴侣加载 Vosk，按住双触点 2U 键录音，松键后在本地转写到草稿；空闲、断线和 BLE 模式均不采样，单段最长 60 秒。A3 可用 `--mic computer`。
- A4 KiCad ERC/DRC/原理图一致性均 0；524,288 键态穷举及 8 个 STL 闭合检查通过，ESP32-S3 固件编译、USB/BLE 主机模拟和伴侣音频解析测试通过。ngspice 每版 129 个工况，A4 接入电荷 38.5–96.6 µC，模型最大过冲约 6.02 V，LED 最低 4.357 V。**仅限工程样机**：按 `docs/validation.md` 实测热插拔、挂起、PDM 波形、装壳拾音及首件配合后再决定量产。
- A4 本地候选 `release/v0.1.0-alpha.4/`，含源码、固件、Gerber、仿真与校验文件。带壳 KiCad 渲染 `build/review/GOWUJI-RevA4-assembled.png`，可打开 `build/review/assembly-preview-a4.kicad_pcb` 按 Alt+3 查看。未推送 GitHub、未创建远程标签或 Release，发布仍须用户明确同意。

- 2026-11-13（第 9 轮，正反面外观）：根据用户给的原厂参考照片，增加独立 A4 外观选件。正面改圆角边框、内嵌面板、浅凹键帽、触摸标记、低 USB 盖；背面加浅边线和 Ø76 mm 单独打印圆盘，圆盘中央图标凹刻约 0.65 mm。外壳底边延长 1.8 mm 以避开末排按键，PCB、固件和原 A4 候选包未改。12 个新 STL 网格闭合，CAD 检查 4 mm 键程、USB 插头、拾音孔、圆盘及安装位无干涉，实物公差与材料质感仍待验证。
- 外观选件源码 `mechanical/appearance.py`，复现和打印说明 `docs/appearance.md`，验证和 KiCad 渲染用 `tools/review_appearance.py`。本地 `build/appearance/` 含 `front.png`、`rear.png`、`appearance-preview.kicad_pcb`、打印与 STEP 压缩包 `GOWUJI-A4-appearance.zip`。未上传 GitHub 或发布 Release。

- 第 10 轮（去除正面凸盖）：用户指出参考图的面板没有前一版顶边中央白色凸起。确认该件是为遮盖 A4 的 Waveshare USB 模块而加的可拆打印盖；从 A4 外观选件、KiCad 预览和 ZIP 移除。USB-C、BOOT 和 RESET 保留在顶边开口内；检查模块、插头、板载麦克风拾音孔和 4 mm 键程无几何干涉，11 个新 STL 均闭合。背面凹刻圆盘、A4 PCB、固件与原 alpha.4 候选包未改，未上传 GitHub。

- 2026-11-14（第 11 轮，Rev B 3D 渲染）：使用 KiCad 9 命令行对当前 Rev B 外观预览 `build/rev-b-shell/appearance-preview.kicad_pcb` 重新渲染，启用高质量、地面阴影和透视。输出 1992×1488 三视图：`build/review/GOWUJI-RevB-front-3D.png`、`GOWUJI-RevB-rear-3D.png`、`GOWUJI-RevB-usb-3D.png`。已目视确认连续正面、键位、背面装饰盘及后置 USB-C 开口显示正常，未发现明显模型穿插。本轮只生成审阅图并更新记录，未改 PCB、外壳、固件或发布包，未上传 GitHub。

- 2026-11-14（第 12 轮，Rev B 仿真与打样判断）：实查板载 ESP32-S3 Rev B 为四层摆件板，0 条铜线/过孔对象、0 个覆铜区；ERC 0、规则违规 0、原理图一致性差异 0，但 DRC 有 210 项未连接。网表核对两面 USB 数据、CC、供电和 PDM，524,288 个触点组合无鬼键/漏键。新增 `tools/simulate_rev_b.py` 跑 USB 输入无源瞬态初筛：64 组中 16 组超过 6 V，最高 8.33 V；这是简化模型，未计入主机限流、稳压器启动和实际 PCB。放行记录及复现命令见 `docs/rev-b-validation.md`，原始报告和最差电路在 `build/rev-b-validation/`。
- **Rev B 当前不可下单打样或试产。** 先解决 VBUS 过冲、完成 PCB 布线并复查 USB、射频、3.3 V 电源及制造文件，再做 3–5 套工程样机；首件验证后才安排小批。可先独立打印外壳。A4 工程候选与其仿真不能代用。未改 PCB 或既有发布包，未推送、打远程标签或发布 GitHub Release。
- Rev B 固件用本地 ESP32 Arduino 3.3.7（4 MB Flash、QSPI PSRAM）编译通过，合并镜像在 `build/firmware-rev-b/Gowuji.ino.merged.bin`；未做实物烧录。

- 2026-11-14（第 13 轮，Rev B 开始走线）：主板 `hardware/rev-b/Gowuji-RevB.kicad_pcb` 已保存 574 段走线、69 个过孔、4 个接地覆铜区。USB 数据、CC、VBUS、晶振、U.FL 射频与地已连通；VBUS 内层主干 0.50 mm，第一内层保留为地参考，底面 LDO 的包络及 0.5 mm 余量通过底壳 CAD 检查。ERC 0、PCB 其他规则违规 0、原理图一致性差异 0；未连接项从 210 降到 **29**，集中在 ESP32 引脚扇出及部分摇杆和 LED 信号。报告和铜层 SVG 在 `build/rev-b-routing/`，手工关键走线初稿脚本为 `tools/route_rev_b.py`。
- Rev B 仍不可下单：先收完飞线，处理 VBUS 热插拔过冲，按实际叠层核对 USB/射频阻抗，再验证 3.3 V 和 LDO 温升。未生成生产包，未推送、打远程标签或发布 GitHub Release。

- 2026-11-14（第 14 轮，Rev B 继续走线）：已保存 910 段走线、105 个过孔、4 个接地覆铜区。KiCad ERC 0、DRC 其他规则违规 0、原理图一致性差异 0；未连接从 29 降为 **11**，剩余均在 ESP32 扇出（CHIP_EN、ENC_A、PDM、触摸、ROW1–3、COL2–3 和 CPU 3.3 V）。报告及 F.Cu 预览在 `build/rev-b-closure/`。本轮接通的 RTC 3.3 V 走线旁补了地过孔，维持原设计规则。
- VBUS 扩展 ngspice 初筛：现设计峰值 9.55 V；候选采用 0.47 Ω 公共串阻和 2.7 Ω/2.2 Ω 电容支路阻尼，1,728 组中板内峰值 5.27 V、连接器端 5.85 V，400 mA 时公共串阻带来最高约 0.197 V 压降。尚未上板，下一步核对低压与负载余量、电源启动和实际板厂阻抗。Rev B 仍不可下单；未生成生产包、未推送或发布。复现步骤见 `docs/rev-b-validation.md`。

- 2026-11-14（第 15 轮，Rev B 布线闭合）：合入 ESP32 西、南、北三处扇出，未连接从 11 降为 **0**，其他 DRC 违规、ERC 和原理图一致性差异均为 0。主板 1,599 段走线、163 个过孔、4 个接地覆铜区；小间距扇出用 0.40 mm 焊环外径、0.20 mm 钻孔和局部最低 0.14 mm 顶层走线间距，须纳入板厂核对。复位线绕过 U.FL 禁布区。报告在 `build/rev-b-closure/`。
- Rev B 已闭合布线，**仍不可下单**：VBUS 过冲的改动尚未上板，低压带载、USB/射频阻抗和下单文件待验证。没有推送或发布。

- 2026-11-14（第 16 轮，Rev B 加入输入阻尼）：主板新增 R16 0.82 Ω 公共串阻、R17 1.5 Ω 电容支路阻尼，C10 改 2.2 µF 直连旁路。1,661 段走线、168 过孔、4 个接地覆铜区；ERC、DRC、未连接、原理图比对均 0。新电阻底壳包络余量通过 0.5 mm CAD 检查，网表及 524,288 键态穷举通过。
- ngspice 当前板 1,728 个热插拔工况：板内 VBUS 5.25 V、插座端最高 6.20 V、前 100 µs 电荷 41.2 µC；R16 最重的单次脉冲电流或能量分别达 4.50 A 和 64.7 µJ。512 个带载工况下，USB 与约束 BLE 预算分别最高 400.3/469.8 mA；无约束 BLE 压力工况 578.7 mA。实际接触反弹、挂起和装壳温升待样机。报告 `build/rev-b-power/`。
- 已生成本地 Gerber、分离钻孔、BOM 和坐标审阅件 `build/rev-b-fab-review/`。**暂不下单**：优先按嘉立创 JLC04161H-3313 核对 USB 90 Ω / 射频 50 Ω，再确认脉冲料号、贴装旋转与工艺，关闭后出 3–5 套工程样机包。未推送、未打远程标签或发布。
- 新的 Rev B 专用固件编译通过，限制 BLE 广播和默认发射功率为 0 dBm；合并镜像已更新。USB 平行干线与 U.FL 馈线下方有完整第一内层地，插座两面的数据分支有约 7.39/4.12 mm 等效几何差，随阻抗一起修正。详情见 `docs/rev-b-validation.md`。

- 2026-11-14（第 17 轮，Rev B 阻抗与制造审阅）：主板加入 JLC04161H-3313 叠层，USB 插座改全顶层、去掉 4 个信号过孔，插座至 MCU 的两种插向几何路径差从 7.39/4.12 mm 降到 5.77/3.48 mm；USB 主段、插座并线及两段射频干线下方全线宽均有 L2 地。射频主段从 0.28 改 0.16 mm；二维模型 USB 主段约 90 Ω、射频约 50 Ω（此前约 37 Ω）。当前 1,657 段走线、164 个过孔，ERC、DRC、未连接及板图一致性均为 0；524,288 组合网表检查复跑通过。
- U1 改本地 S3 封装，保留铜与散热孔，调整 16 个锡膏窗，覆盖约 53%，锡膏到钻孔标称最少约 0.13 mm。制造审阅件重新导出：202 个镀孔、45 个非镀孔，98 外加 1 个混装点位，其中纯 SMT 78 个；详见 `docs/rev-b-fab-notes.md`。**继续暂缓下单**：核定阻尼器件的脉冲与直流偏压、板厂阻抗及 PCBA 旋转，随后生成可供 3–5 套工程样机的下单件。未推送或发布。

- 2026-11-16（第 18 轮，PCB + 工厂贴装打样准备）：用户选择 3–5 套工程样机。新增 `hardware/rev-b/assembly-parts.csv`，按位号覆盖 105 个封装；R16 锁定 Bourns CRM1206-FX-R820ELF、R17 Vishay CRCW06031R50FKEAHP，核对厂商脉冲曲线；C10/C14/C15/C8 锁定村田料号并核对公开偏压数据。LED 总有效容量从旧模型固定 45 µF 改为 12–62 µF，输入容量上限也扩展。PCB 铜几何未改。
- 最新 ngspice：1,728 个热插拔工况，板内最高 5.25 V、插座侧 6.20 V、前 100 µs 电荷 46.17 µC；R16/R17 脉冲最高 16.01/6.69 W，按所选曲线保守界限初筛通过。1,024 个带载工况，正常 USB/约束 BLE 峰值约 402/472 mA。启动简化模型约 110 mA，**未证明 USB 枚举前 100 mA 预算满足**，须首件实测并视结果调整启动/使能；挂起、热插拔、温升、RF 等仍待实物验证。
- KiCad 9.0.8 ERC、DRC、未连接、板图一致性均 0；524,288 键态通过，USB/BLE 主机固件模拟和两项音频解析测试通过；ESP32 Arduino 3.3.7 + NeoPixel 1.15.2 的 Rev B 固件编译通过，4 MB 合并镜像已纳入包。独立 Gerber 解析确认四铜层、202 PTH/45 NPTH、95×98 mm 外形；实际最细线 0.10 mm，最小过孔 0.20/0.40 mm。
- 最终本地交厂包 `build/rev-b-pcba.zip`，SHA256 `cc030c8adb076927003157e7023ff04864ddde03414a36b665c9f753773d19af`；含 Gerber 子包、78 SMT + 1 USB 混装 BOM/CPL、14 后焊件表、极性图、源文件、仿真及固件。导出脚本 `tools/export_rev_b_order.py` 拒绝旧目录混入，检查规则、层/孔、BOM/坐标和全部交付哈希。下单及工艺说明 `docs/rev-b-order.md`，元件审核 `docs/rev-b-component-review.md`。
- **可提交报价/CAM，尚不能声称工厂已确认开工**：待工厂回签指定叠层/阻抗、QFN 散热孔与钢网工艺、齐料/替代料及器件旋转；目前无工厂反馈、订单或付款。资料侧工作已完成，完整“可以开工打样”目标仍等这些外部确认。用户可按说明中的询价文本提交；收到回复后继续关闭问题。未推送、未创建远程标签或发布 GitHub Release。

- 2026-11-16（第 19 轮，启动风险复核）：再次检查当前固件与交厂包网表：U3 TPS22918 的 ON（3 脚）直接接 V3V3，没有 MCU 独立使能；因此不能仅延迟 `pixels.show()` 就消除 LED 电源上电充电电流。当前固件未处理 USB 挂起事件，不能把软件模拟通过当作挂起功耗验证。这两项继续属于工程首件必测项；若实测失败，可能需要硬件使能改版或电源管理修改。未把有待实测的模型风险擅自当成已定位故障，也未改变当前制造包。
- 当前完整打样包及本地提交 `77ae4fc` 保持有效；工厂叠层/阻抗、QFN 工艺、齐料、旋转确认仍缺失。用户明确回复“尚未提交工厂”，不存在待轮询的工厂审核任务；需先由用户提交完整包取得实际反馈。不能据本地 ERC/DRC 宣布全目标完成。未联系工厂、下单、付款或远程发布。

- 2026-11-16（第 20 轮，等待工厂审核）：复核交付 ZIP SHA256 与全部设计输入哈希仍一致，工作树在复核前干净。连续三轮的剩余阻碍均为实际工厂审核缺失，且用户已确认未提交；没有运行中的外部审核可轮询，也不能以本地重复检查代替工厂确认。目标标记为 blocked（等待外部反馈），不是 complete。恢复条件：取得工厂对本包的叠层/阻抗、QFN 工艺、齐料/替代料和旋转审核意见，随后按具体意见修订、复查并重新导出。未改变制造包，未上传、下单或发布。

- 2026-11-16（第 21 轮，用户指定代交华秋）：用户明确授权“帮我提交给华秋”，按 PCB+SMT 首批5套推进；此授权仅适用于华秋提交，不改变 GitHub 发布许可要求。核查官方活动：PCB新客四层券上限200元，SMT首单优惠不包含元器件/DIP等；账号资格和实际报价未确认，未承诺整单免费。
- 新增 `tools/package_huaqiu_rfq.py`、`docs/rev-b-huaqiu.md`，输出 `build/huaqiu-rfq.zip`（SHA256 `2374de7a1bf5f4d6eb8c8c991f1880157866d6cb4d4b440a6908246cd60b4413`）。按华秋建议合并相同MPN，35行BOM/93位号，与93行坐标一致，含14个后焊位号；附装配方向与工艺说明。华秋网页实际选择四层1.6mm内铜0.5oz后显示7628外侧介质0.20mm/Dk4.2，与现板0.0994mm/Dk4.1不同；须先回签定制叠层或按实际叠层改线，不能直接用默认叠层生产。当前仅为询价审核包，未改PCB。
- 已经用华秋 PCBA 网页实际上传 Gerber，页面显示上传成功且解析成功。BOM及坐标尝试上传均返回“未登录”，网站弹出微信登录二维码；**未生成订单号、未付款、未完成PCBA提交**。页面证据在 `build/huaqiu-review/`，最新二维码 `login-qr.png`。当前自己的 Chrome 会话使用 `.local/huaqiu-profile`，CDP `http://127.0.0.1:9223`，进程由 exec session 62551 启动；继续前必须检查会话是否仍活跃，不能仅凭记录假定登录成功。
- 曾推荐 TinyFish 插件，但未确认安装/连接；随后已有网页自身扫码登录路径，用户可直接扫码确认此浏览器会话，不需要发送密码或验证码。登录后重新上传BOM/CPL、领取适用优惠、填写并核对工艺/地址与价格，再按已授权范围提交审核；有费用时列出具体金额交用户决定，不擅自付款。等待登录是本次恢复后的新阻碍，仅出现本轮，不重复宣告blocked或complete。未推送或发布GitHub。

- 2026-11-16（第 22 轮，华秋报价及收货地区）：扫码后曾确认登录成功，重新上传 Gerber、35行BOM、93行坐标及完整工艺附件，页面显示文件已上传；四层板200元券领取成功，尚未确认实际抵扣。已填写5块四层板、5套双面贴装、指定叠层/阻抗及报告、U1九孔填孔封帽要求、5片X-ray、人工生产稿和样品图确认。研发型优惠有3项不满足，保留工程审核要求，按标准型询价；没有改PCB或原交付包。
- 用户已提供收件信息，仅用于华秋履约，不写入仓库。当前计价页只选择省市，已填广东/广州，选京东标快16元；姓名、电话、区及详细地址尚未进入订单收货表。当前稳定预估为PCB988元、SMT及运费288.33元，总计1276.33元含税；活动已减842.98元，BOM仍待人工报价，200元券尚未计入。价格仅供参考，以人工审核为准；报价证据在 `build/huaqiu-review/quote-estimate.txt`。
- 已向用户询问是否按此费用水平继续提交未付款审核订单，或先优化成本。尚未点击立即下单，没有订单号、未付款、工厂未回签。继续时网页页头又显示未登录，已打开新扫码框，二维码为 `build/huaqiu-review/login-qr-current.png`；不能凭先前登录记录假定仍有会话。表单与上传文件保留，下一步先确认费用选择及登录，再完成订单收货信息和实际审核提交。未推送或发布GitHub，目标未完成。

- 2026-11-16（第23轮，用户选择降本、暂不下单）：停止订单提交。登录随后恢复，但页面刷新清空上传文件；现网页仅用于参数试算，备注明确不下单、不生产。逐项比较发现现成2116/7628使PCB含税988→652元，1080为710元；单面贴装名义费下降被当前活动减免同步减少抵消，净费用不降，不搬动底面电源件。0.25mm孔只省2元且试改15孔新增12处间距违规，放弃；0.30mm孔理论省118元但需重做QFN扇出，未实施。详见 `docs/rev-b-huaqiu-cost.md`。
- 已新增 `tools/prepare_huaqiu_cost_candidate.py`，独立生成 `build/huaqiu-cost-review/hq2116/` 的REVIEW ONLY候选：USB16段主线0.18→0.22mm、RF6段0.16→0.21mm，保留QFN短逃线，其余拓扑/器件/原理图不变；重填铜后DRC违规、未连接、原理图一致性均0，3684个采样点确认加宽线下有L2地参考。二维模型在2116的0.125mm/Dk4.2假设下USB约89.20Ω、RF约49.19Ω。模型支持可选阻焊厚度，原默认参数未改。
- 候选预计PCB省336元；若原其它费用不变，总计推算940.33元，未含BOM、未抵200元券，不是正式完整报价。本轮无文件试算DIP为100.50元而原带文件报价118元，不能直接比较两轮整单数字。公开2116铜箔字段与名义厚度有歧义，必须回签实际压合叠层及成品铜厚后才能定版导出。原Rev B设计和交厂ZIP保持原状，没有导出候选生产Gerber、没有上传候选、没有订单或付款。用户“暂不下单”持续有效；未推送、未发布，完整打样目标仍未完成。

- 2026-11-16（第24轮，PCB成品外观预览）：从HQ2116独立候选用KiCad 9实际渲染正反面板体视图，输出 `build/huaqiu-cost-review/render/pcb-top.png`、`pcb-bottom.png`（1400×1200），已目视确认板框完整、焊盘/孔位/丝印可见。展示为PCB板体3D预览，并非实物照片或完整贴装成品图；USB-C指定模型缺失，未把不完整器件渲染当成完整装配。仅使用临时预览副本解析模型路径，没有改变原版或候选电气设计、生产包，没有下单、付款或远程发布。

- 2026-11-17（第25轮，KiCad 打样前复核）：用本机 KiCad 10.0.7 CLI 对 `hardware/rev-b/` 原版和 `build/huaqiu-cost-review/hq2116/` 候选重跑检查，两者均 ERC 0、未连接 0、原理图一致性 0；DRC 各仅 1 条 warning：J3 U.FL 板载封装与 KiCad 10 库存副本不一致。核对为整个封装（焊盘/丝印/文字）相对库存版本平移 +0.475 mm，3D 模型 offset 同步 +0.475，内部几何与装配关系一致，不是间距或连接错误，不影响 Gerber/BOM/坐标。
- 原版板仍与交厂包 `build/rev-b-pcba.zip`（SHA256 `cc030c8adb076927003157e7023ff04864ddde03414a36b665c9f753773d19af`）内 `source/hardware/rev-b/Gowuji-RevB.kicad_pcb` 逐字节一致，ZIP 哈希与第18轮记录一致。板 95×98 mm、4 铜层，叠层为 JLC04161H-3313（3313 0.0994 mm/Dk4.1），1657 段走线、164 过孔（149×0.6/0.3、15×0.4/0.2）、8 个铜区、105 封装、375 焊盘；装配 BOM 79 行、CPL 79 行、14 个后焊位号。
- 结论：**设计侧已具备打样条件，可按原版 Rev B/JLC 叠层提交 3–5 套工程样机**；KiCad 不能替代工厂回签，下单前仍需确认叠层/阻抗、QFN 散热孔与钢网、齐料/替代料和旋转。HQ2116 候选仍为 REVIEW ONLY，未回签实际压合叠层前不得作为生产版。USB 枚举前 100 mA、挂起、热插拔、温升、装壳拾音等仍列首件实测。
- 复核报告和渲染在 `build/preflight-2026-11-17/`。本轮未改设计、交厂包或候选，未下单、未推送、未发布。

- 2026-11-17（第26轮，Rev B 3D 渲染）：用 KiCad 10.0.7 CLI 从 `hardware/rev-b/Gowuji-RevB.kicad_pcb` 高质量渲染顶部斜视、底部斜视和正上方三张 1800×1350 图，输出 `build/preflight-2026-11-17/render/revb-iso-top.png`、`revb-iso-bottom.png`、`revb-top.png`。已目视检查键位、旋钮、摇杆、触摸片、丝印和底部地铜/过孔显示正常；键帽为项目简化模型，当前 `build/` 中没有带壳装配预览文件，故未渲染外壳。未改设计或交厂包，未推送、未下单。

- 2026-11-17（第27轮，PCB 与整机 3D 重渲染）：用 uv 建 `.local/cq-venv`（Python 3.12 + cadquery 2.8）重新生成 Rev B 外壳与键帽模型到 `build/rev-b-shell/`，`mechanical/appearance.py --rev-b` 导出 base/face/enclosure/7 个键帽/旋钮及预览 STEP；`tools/review_appearance.py --rev-b-board hardware/rev-b/Gowuji-RevB.kicad_pcb` 校验 11 个闭合网格、后盖座、USB 开口、麦克风和 4 mm 键程通过，并生成 `appearance-preview.kicad_pcb`。
- KiCad 10.0.7 渲染：PCB 板级顶/底斜视 `build/preflight-2026-11-17/render/revb-pcb-iso-top.png`、`revb-pcb-iso-bottom.png`；整机（带外壳）前/后/USB 侧 `build/rev-b-shell/revb-product-front.png`、`revb-product-rear.png`、`revb-product-usb.png`，均 1992×1488、高质量、地板阴影和透视。已目视确认连续正面、六状态键（统一 agent 图标）、动作键图标、旋钮/摇杆、触摸标记、后盖圆盘凹刻和 USB 开口位置；USB-C 精确 3D 模型在本机 KiCad 10 库中缺失，开口处会看到裸 PCB 与丝印，仅为渲染外观问题。
- 未改设计、原理图、PCB、交厂包或候选；新增文件均在 `build/` 和 `.local/`（已忽略）。未推送、未下单。
