# v0.1.0-alpha.1 · GOWUJI Rev A

第一版低成本样机，包含 KiCad 原理图与双层 PCB、13 个机械键、五向摇杆、按压旋钮、触摸、六路 RGB、3D 打印件和 BOM。固件含 USB HID、USB CDC 以及可选 BLE HID。Codex 伴侣通过公开 App Server 管理六个聊天槽和状态灯，可用可配置提示词、审批键与本地语音输入。

附件：

- `GOWUJI-v0.1.0-alpha.1-source.zip`：项目源码、KiCad 文件、STL、STEP、BOM 和文档。
- `GOWUJI-v0.1.0-alpha.1-flash-0x0.bin`：适用于 Waveshare ESP32-S3-Zero 的 4 MB 合并镜像，写入地址 `0x0`。
- `GOWUJI-v0.1.0-alpha.1-gerber.zip`：裸板打样文件。
- `GOWUJI-v0.1.0-alpha.1-review.zip`：PCB 和原理图预览、检查报告、BOM。
- `SHA256SUMS.txt`：附件校验值。

这是未经实物验证的预发行版本。BLE HID 需要 USB-C 外接 5 V 电源；聊天状态同步使用 USB。伴侣应用不依赖原厂设备识别。

固件构建依赖：[Arduino ESP32 3.3.7](https://github.com/espressif/arduino-esp32/tree/3.3.7)、[Adafruit NeoPixel 1.15.2](https://github.com/adafruit/Adafruit_NeoPixel/tree/1.15.2)。源码包提供固件及构建脚本，可安装或替换这些依赖重新编译。
