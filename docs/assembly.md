# Rev A 打样、装配和上电

1. 下单用 Gerber ZIP。选 2 层 FR-4、1.6 mm、1 oz、普通阻焊和无铅喷锡；图纸是单块 95 × 98 mm。两个钻孔文件分别为 PTH 与 NPTH。小批量建议先只做一批裸板，自行装一台检查后再考虑 PCBA。
2. 用 PLA 或 PETG 打印底壳和面板，建议 0.20 mm 层高、0.4 mm 喷嘴、三道外壁。面板 STL 已把外表面翻到打印床，先用一个廉价轴试卡 14.05 mm 开口。导光件用透光或半透明材料，必要时少量点胶。面板背面触摸区贴 14 mm 方形铜箔，导线接 J1，装拆时给线留余量；铜箔不能碰到螺钉或屏蔽件。
3. 先焊贴片。D1–D19 的色带为阴极，PCB 上每个二极管的短丝印线对应阴极；D15–D19 的网络接法与其余二极管不同，所有器件仍按各自丝印方向装。注意 U2 的 1 脚、LED1–LED6 的 1 脚、SW15 的 1 脚。五向开关指定 SKRHAAE010（无定位柱），不直接替换为带柱型号。旋钮指定 EC11E15244G1（推按、20 mm D 形轴）。
4. 插入模块，USB-C 朝板边，用板上两排 9 针焊孔。放置托盘、PCB、面板并先干装；穿过面板插入 MX 轴，卡好后焊。四枚 M2×10 螺钉依次对角轻紧。电烙铁和冲击力勿传到打印件。摇杆帽和旋钮先试套，不合适时可按打印机公差微调 STEP 或 CadQuery。
5. 首次上电前，用万用表检查 VBUS 与 GND 是否短路；用限流 USB 电源或可测电流的 USB 供电。无需触碰触摸区，给电后会采集基线。若无法找到烧录口，按住模块 BOOT，点按 RESET，再松开 BOOT；选择新出现的串口，烧录合并镜像到地址 `0x0`，完成后复位。这个镜像覆盖 4 MB 闪存，不适用于原厂 Codex Micro。
6. 装整机前在桌面依次确认：13 键、组合键、旋钮两方向和按压、摇杆五方向、触摸、六颗 RGB 灯、USB 数据、蓝牙配对。若要无线运行，用支持小电流设备的 USB 电源或充电宝；测试其低电流自动关断行为。不要从 U1 的 5 V 焊点反向供电。

固件量产烧录只需 Release 的 `*-flash-0x0.bin`。Windows 示例：`python firmware/flash.py COM6 <镜像路径>`。确认镜像和源码与 Release 的 `SHA256SUMS.txt` 一致。建议实测约束：按键测试无鬼键或卡键，LED 显示与槽号一一对应，断开伴侣后应恢复普通 HID，蓝牙重连不应残留按下状态。触摸阈值见 `readTouch()`；连接 USB 后发送 `HELLO GOWUJI/1` 与 `TOUCH?` 可查询当前值和基线。

参考资料：[ESP32-S3-Zero 官方引脚图与原理图](https://docs.waveshare.com/ESP32-S3-Zero/Resources-And-Documents)、[ALPS EC11E15244G1](https://tech.alpsalpine.com/e/products/detail/EC11E15244G1/)、[ALPS SKRHAAE010](https://tech.alpsalpine.com/e/products/detail/SKRHAAE010/)、[WS2812B-Mini 数据表](https://www.tme.eu/Document/01c0100fee68667af99767edc3a7fee2/WS2812B-MINI.pdf)。
