# v0.1.0-alpha.3 · GOWUJI Rev A3

Rev A3 按原厂键位重排：左上旋钮、右上摇杆、上两排六个磨砂透光状态键、左下触摸片和底排 2U 语音键。双轴长键在固件中合并为单一动作。新版含重布线 PCB、面板、双轴键帽、可拆 USB 盖、带外壳的 KiCad 预览及仿真结果；保留 A2 的灯组软启动。请配套使用 A3 PCB、面板和固件。

附件：

- `GOWUJI-v0.1.0-alpha.3-source.zip`：项目源码、KiCad 文件、STL、STEP、BOM 和文档。
- `GOWUJI-v0.1.0-alpha.3-flash-0x0.bin`：适用于 A3 的 Waveshare ESP32-S3-Zero 4 MB 合并镜像，写入 `0x0`。
- `GOWUJI-v0.1.0-alpha.3-gerber.zip`：裸板打样文件。
- `GOWUJI-v0.1.0-alpha.3-review.zip`：PCB、原理图、两张 KiCad 3D 图、检查报告、仿真数据和 BOM。
- `SHA256SUMS.txt`：附件校验值。

这是工程样机版。KiCad 检查及矩阵仿真通过；量产须先完成 [USB 热插拔及整机首件验证](validation.md)。BLE HID 需要 USB-C 外接 5 V 电源；聊天状态同步使用 USB。

固件构建依赖：[Arduino ESP32 3.3.7](https://github.com/espressif/arduino-esp32/tree/3.3.7)、[Adafruit NeoPixel 1.15.2](https://github.com/adafruit/Adafruit_NeoPixel/tree/1.15.2)。源码包提供固件及构建脚本，可安装或替换这些依赖重新编译。
