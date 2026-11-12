# v0.1.0-alpha.2 · GOWUJI Rev A2

Rev A2 加入灯组电源软启动和矩阵外部上拉，修正 RGB 焊盘，增厚 USB 开口附近的面板，加入 MX 轴孔试片和 KiCad 器件 3D 模型。固件更新按键扫描及串口断开时的按住说话恢复逻辑。Codex 伴侣继续通过公开 App Server 管理六个聊天槽和状态灯。

附件：

- `GOWUJI-v0.1.0-alpha.2-source.zip`：项目源码、KiCad 文件、STL、STEP、BOM 和文档。
- `GOWUJI-v0.1.0-alpha.2-flash-0x0.bin`：适用于 Waveshare ESP32-S3-Zero 的 4 MB 合并镜像，写入地址 `0x0`。
- `GOWUJI-v0.1.0-alpha.2-gerber.zip`：裸板打样文件。
- `GOWUJI-v0.1.0-alpha.2-review.zip`：PCB 和原理图预览、KiCad 3D 渲染、检查报告、仿真数据和 BOM。
- `SHA256SUMS.txt`：附件校验值。

这是工程样机版。KiCad 检查及矩阵仿真通过；量产须先完成 [USB 热插拔及整机首件验证](validation.md)。BLE HID 需要 USB-C 外接 5 V 电源；聊天状态同步使用 USB。

固件构建依赖：[Arduino ESP32 3.3.7](https://github.com/espressif/arduino-esp32/tree/3.3.7)、[Adafruit NeoPixel 1.15.2](https://github.com/adafruit/Adafruit_NeoPixel/tree/1.15.2)。源码包提供固件及构建脚本，可安装或替换这些依赖重新编译。
