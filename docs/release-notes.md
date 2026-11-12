# v0.1.0-alpha.4 · GOWUJI Rev A4

Rev A4 增加 PCB 上的数字 MEMS 麦克风和面板左上方拾音孔，沿用 A3 键位及灯组软启动。USB 模式下按住 2U 长键说话，松开后由伴侣本地转写到草稿。请配套使用 A4 PCB、面板、固件和伴侣。

附件：

- `GOWUJI-v0.1.0-alpha.4-source.zip`：项目源码、KiCad 文件、STL、STEP、BOM 和文档。
- `GOWUJI-v0.1.0-alpha.4-flash-0x0.bin`：适用于 A4 的 Waveshare ESP32-S3-Zero 4 MB 合并镜像，写入 `0x0`。
- `GOWUJI-v0.1.0-alpha.4-gerber.zip`：裸板打样文件。
- `GOWUJI-v0.1.0-alpha.4-review.zip`：PCB 和原理图预览、两张 KiCad 3D 图、检查报告、仿真数据和 BOM。
- `SHA256SUMS.txt`：附件校验值。

这是工程样机版。KiCad 检查及矩阵仿真通过；量产须先完成 [USB 热插拔、板载录音及整机首件验证](validation.md)。BLE HID 需要 USB-C 外接 5 V 电源；聊天状态和板载录音使用 USB。

固件构建依赖：[Arduino ESP32 3.3.7](https://github.com/espressif/arduino-esp32/tree/3.3.7)、[Adafruit NeoPixel 1.15.2](https://github.com/adafruit/Adafruit_NeoPixel/tree/1.15.2)。源码包提供固件及构建脚本，可安装或替换这些依赖重新编译。
