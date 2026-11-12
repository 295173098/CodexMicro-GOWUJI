#pragma once
#include <BLEDevice.h>
#include <BLEHIDDevice.h>
#include <BLESecurity.h>
#include <atomic>

namespace BleKeys {
inline std::atomic<bool> authenticated{false};
inline BLECharacteristic *input = nullptr;
inline BLECharacteristic *bootInput = nullptr;
inline BLECharacteristic *mode = nullptr;
inline uint8_t report[8]{};

class Connection : public BLEServerCallbacks {
  void onDisconnect(BLEServer *) override {
    authenticated.store(false);
    BLEDevice::startAdvertising();
  }
};
class Security : public BLESecurityCallbacks {
  uint32_t onPassKeyRequest() override { return 0; }
  void onPassKeyNotify(uint32_t) override {}
  bool onConfirmPIN(uint32_t) override { return true; }
  bool onSecurityRequest() override { return true; }
#if defined(CONFIG_BLUEDROID_ENABLED)
  void onAuthenticationComplete(esp_ble_auth_cmpl_t result) override { authenticated.store(result.success); }
#elif defined(CONFIG_NIMBLE_ENABLED)
  void onAuthenticationComplete(ble_gap_conn_desc *result) override {
    authenticated.store(result && result->sec_state.encrypted);
  }
#endif
};

inline void send() {
  if (!authenticated.load()) return;
  auto protocol = mode->getValue();
  auto *dest = protocol.length() && protocol[0] == 0 ? bootInput : input;
  dest->setValue(report,sizeof(report));
  dest->notify();
}

inline void start() {
  static uint8_t descriptor[] = {
    0x05,0x01,0x09,0x06,0xa1,0x01,0x85,0x01,
    0x05,0x07,0x19,0xe0,0x29,0xe7,0x15,0x00,0x25,0x01,0x75,0x01,0x95,0x08,0x81,0x02,
    0x75,0x08,0x95,0x01,0x81,0x01,
    0x05,0x08,0x19,0x01,0x29,0x05,0x75,0x01,0x95,0x05,0x91,0x02,0x75,0x03,0x95,0x01,0x91,0x01,
    0x05,0x07,0x19,0x00,0x29,0x73,0x15,0x00,0x25,0x73,0x75,0x08,0x95,0x06,0x81,0x00,0xc0
  };
  BLEDevice::init("GOWUJI BLE");
  auto *security = new BLESecurity();
  security->setCapability(ESP_IO_CAP_NONE);
  security->setAuthenticationMode(true,false,true);
  BLEDevice::setSecurityCallbacks(new Security());
  auto *server = BLEDevice::createServer();
  server->setCallbacks(new Connection());
  auto *hid = new BLEHIDDevice(server);
  hid->manufacturer("GOWUJI DIY");
  hid->hidInfo(0,2);
  hid->reportMap(descriptor,sizeof(descriptor));
  input = hid->inputReport(1);
  hid->outputReport(1);
  bootInput = hid->bootInput();
  hid->bootOutput();
  mode = hid->protocolMode();
  hid->setBatteryLevel(100);  // Externally powered; there is no battery gauge.
  hid->startServices();
  auto *adv = BLEDevice::getAdvertising();
  adv->setAppearance(HID_KEYBOARD);
  adv->addServiceUUID(hid->hidService()->getUUID());
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
}

inline bool press(uint8_t usage) {
  if (!authenticated.load()) return false;
  for (uint8_t i=2;i<8;i++) if (report[i]==usage) return true;
  for (uint8_t i=2;i<8;i++) if (!report[i]) {
    report[i]=usage;
    send();
    return true;
  }
  return false;
}
inline void release(uint8_t usage) {
  for (uint8_t i=2;i<8;i++) if (report[i]==usage) report[i]=0;
  send();
}
inline void clear() {
  memset(report,0,sizeof(report));
  send();
}
}
