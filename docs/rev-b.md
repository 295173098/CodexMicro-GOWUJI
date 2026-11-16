# Rev B · 直接贴装 ESP32-S3

Rev B 使用 ESP32-S3FH4R2（QFN56，7 × 7 mm，4 MB Flash 和 2 MB PSRAM 在芯片封装内）。USB-C 连接器焊在主 PCB，插口在外壳后侧；正面不再为开发板开窗。沿用 A4 的按键、状态灯、触摸和板载麦克风引脚与软件协议。

初稿按 95 × 98 mm、1.6 mm 四层板设计。40 MHz 晶振、3.3 V 稳压、USB-C CC 下拉与 USB ESD 保护独立贴装。蓝牙用壳内 2.4 GHz FPC 天线，通过 U.FL 接入。天线放在非金属壳内的上边区域，远离背部装饰盘、PCB 大地及 USB 线，装壳后再定安装点。C19、C20 是射频匹配预留，默认不贴；L1 和晶振负载电容都是起始值。单板成本须用四层板和贴装报价重新核算，不能用芯片单价代替整板成本。

首次烧录：开壳，用夹具将 TP1（BOOT）拉低，给 USB 供电或短接 TP2（RESET）到 TP3（GND）后释放 RESET，再释放 BOOT。选择新枚举的串口，烧录 Rev B 镜像到 `0x0`。TP4/TP5 提供 UART 救援；与 LED/PDM 线复用，使用 3.3 V UART，不能注入 5 V。Rev B 已编译生成合并镜像，实物烧录和启动仍待验证。

**工程打样文件已备齐，待工厂 CAM 回签后开工。** 本轮建议 5 块 PCB、3–5 块贴装，按[打样下单说明](rev-b-order.md)使用 `build/rev-b-pcba.zip`。设计检查和扩展仿真见[放行记录](rev-b-validation.md)。这是首件工程验证，尚未证明实物 USB、温升、射频和整机功能通过；不用于量产。

参考：[ESP32-S3 数据表](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)、[Espressif 原理图检查](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)、[PCB 布局建议](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html)。
