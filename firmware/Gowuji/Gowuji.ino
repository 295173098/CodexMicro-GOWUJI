#ifdef GOWUJI_HOST_SIM
#include "sim_hal.h"
#else
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <USB.h>
#include <USBCDC.h>
#include <USBHIDKeyboard.h>
#include "ble_keys.h"
#endif
#include "pins.h"

USBHIDKeyboard keyboard;
USBCDC consolePort;
Adafruit_NeoPixel pixels(LED_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);

namespace {
constexpr uint32_t debounceMs = 8, leaseMs = 2500;
constexpr uint8_t actions = sizeof(KEY_NAMES) / sizeof(KEY_NAMES[0]);
constexpr uint8_t fallback[actions] = {
  0x68,0x69,0x6a,0x6b,0x6c,0x6d,0x6e,0x6f,0x70,0x71,0x72,0x73,0,
  0x65,0x52,0x4f,0x51,0x50,0
};
constexpr uint8_t ledIndex[actions] = {0,1,255,255,2,3,255,255,4,5,255,255,255,255,255,255,255,255,255};
constexpr uint32_t palette[] = {
  0x000000,0x888888,0x2068ff,0x00de55,0xff9100,0xff2030,0xc050ff
};
struct Key {
  uint32_t changed = 0;
  bool raw = false, stable = false, armed = false;
};
Key key[actions];
bool hidDown[actions]{};
uint8_t localLED[LED_COUNT]{}, remoteLED[LED_COUNT]{};
uint8_t layer = 0;
uint32_t alive = 0, touchBaseline = 0, lastTouch = 0, lastScan = 0, lastDisplay = 0, layerFlash = 0;
bool host = false, touched = false, wireless = false, bleWasReady = false;
bool pttDown = false;
int8_t encSteps = 0;
uint8_t encOld = 0;
char line[64];
size_t used = 0;
bool overflow = false;
uint8_t dialTap = 0;
uint32_t dialAt = 0;

uint8_t encoder() { return (digitalRead(ENC_A) << 1) | digitalRead(ENC_B); }
bool hidPress(uint8_t raw) { return wireless ? BleKeys::press(raw) : keyboard.pressRaw(raw) != 0; }
void hidRelease(uint8_t raw) {
  if (wireless) BleKeys::release(raw); else keyboard.releaseRaw(raw);
}
void hidClear() {
  if (wireless) BleKeys::clear(); else keyboard.releaseAll();
  memset(hidDown,0,sizeof(hidDown));
  dialTap=0;
}

void emit(const char *name, int value) {
  if (host && consolePort) consolePort.printf("EV %s %d\n", name, value);
}

void keyEvent(uint8_t i, bool down) {
  if (!down && hidDown[i]) {
    hidRelease(fallback[i]);
    hidDown[i] = false;
  }
  if (ledIndex[i] != 255) localLED[ledIndex[i]] = down ? 2 : 1;
  if (host) {
    emit(KEY_NAMES[i], down);
  } else if (down && fallback[i]) {
    hidDown[i] = hidPress(fallback[i]);
  }
}

void sample(uint8_t i, bool on, uint32_t now) {
  auto &k = key[i];
  if (k.raw != on) {
    k.raw = on;
    k.changed = now;
  }
  if (now - k.changed < debounceMs) return;
  if (!k.armed) {
    k.armed = !on;  // Suppress keys held through boot.
    return;
  }
  if (k.stable != on) {
    k.stable = on;
    if (i != PTT_PRIMARY && i != PTT_SECONDARY) keyEvent(i, on);
  }
}

void readMatrix(uint32_t now) {
  for (uint8_t r = 0; r < 4; ++r) {
    digitalWrite(ROWS[r], LOW);
    pinMode(ROWS[r], OUTPUT);
    delayMicroseconds(25);  // Allow a released column to rise through its 22k pull-up.
    for (uint8_t c = 0; c < 5; ++c) {
      int i = MATRIX[r][c];
      if (i >= 0) sample(i, digitalRead(COLS[c]) == LOW, now);
    }
    pinMode(ROWS[r], INPUT);  // Other rows float, including while a chord is held.
  }
  // Either switch under the shared 2U cap holds PTT; only release once both release.
  const bool down = key[PTT_PRIMARY].stable || key[PTT_SECONDARY].stable;
  if (down != pttDown) {
    pttDown = down;
    keyEvent(PTT_PRIMARY, down);
  }
}

void readEncoder() {
  static constexpr int8_t quad[] = {0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};
  uint8_t n = encoder();
  if ((n ^ encOld) == 3) encSteps = 0;
  else encSteps += quad[(encOld << 2) | n];
  encOld = n;
  if (abs(encSteps) < 2) return;  // EC11E15244G1: 30 detents, 15 pulses.
  int direction = encSteps > 0 ? 1 : -1;
  encSteps = 0;
  if (host) emit("DIAL", direction);
  else {
    uint8_t raw = direction > 0 ? 0x4b : 0x4e;
    if (dialTap) hidRelease(dialTap);
    dialTap = hidPress(raw) ? raw : 0;
    dialAt = millis();
  }
}

void readTouch(uint32_t now) {
  uint32_t v = touchRead(TOUCH_PIN);
  if (!v || !touchBaseline) return;
  bool next = uint64_t(v) * 100 > uint64_t(touchBaseline) * (touched ? 112 : 125);
  static uint8_t count = 0;
  if (next == touched) count = 0;
  else if (++count >= 3) {
    count = 0;
    touched = next;
    if (next) {
      layer = (layer + 1) % 6;
      layerFlash = now + 440;
      emit("PROFILE",layer);
    }
    emit("TOUCH", next);
  }
  if (!touched && !next) touchBaseline = (uint64_t(touchBaseline) * 31 + v + 16) / 32;
}

void command(const char *s, uint32_t now) {
  if (strcmp(s,"HELLO GOWUJI/1") == 0) {
    if (!host) {
      hidClear();
    }
    host = true;
    alive = now;
    consolePort.println("OK GOWUJI/1");
    emit("PROFILE",layer);
    emit("PTT_STATE",pttDown);
  } else if (host && strcmp(s,"PING") == 0) {
    alive = now;
    consolePort.println("PONG");
  } else if (host && strncmp(s,"LED ",4) == 0 && strlen(s) == 10) {
    for (uint8_t i=4;i<10;i++) if (s[i]<'0' || s[i]>'6') return;
    for (uint8_t i=0;i<LED_COUNT;i++) remoteLED[i] = s[i+4] - '0';
    alive = now;
  } else if (host && strcmp(s,"TOUCH?") == 0) {
    consolePort.printf("TOUCH %lu %lu\n",(unsigned long)touchRead(TOUCH_PIN),(unsigned long)touchBaseline);
  }
}

void serialInput(uint32_t now) {
  if (host && (!consolePort || now - alive > leaseMs)) {
    host = false;
    memset(remoteLED,0,sizeof(remoteLED));
  }
  for (int i=0; i<96 && consolePort.available(); ++i) {
    int c = consolePort.read();
    if (c=='\r') continue;
    if (c=='\n') {
      if (!overflow) {
        line[used]=0;
        command(line,now);
      }
      used=0;
      overflow=false;
    } else if (!overflow && c>=32 && c<=126 && used < sizeof(line)-1) {
      line[used++] = char(c);
    } else {
      overflow = true;
    }
  }
}

void display(uint32_t now) {
  for (uint8_t i=0;i<LED_COUNT;i++) {
    uint8_t color = host ? remoteLED[i] : localLED[i];
    if (int32_t(layerFlash-now)>0 && layer == i) color = 6;
    pixels.setPixelColor(i,palette[color]);
  }
  pixels.show();
}
}

void setup() {
  for (auto r: ROWS) pinMode(r,INPUT);
  for (auto c: COLS) pinMode(c,INPUT);
  // Hold the encoder's push switch during reset to choose BLE for this boot.
  digitalWrite(ROWS[2],LOW);
  pinMode(ROWS[2],OUTPUT);
  delay(15);
  wireless=digitalRead(COLS[3])==LOW;
  pinMode(ROWS[2],INPUT);
  pinMode(ENC_A,INPUT_PULLUP);
  pinMode(ENC_B,INPUT_PULLUP);
  encOld = encoder();
  pixels.begin();
  pixels.setBrightness(45);
  pixels.clear();
  USB.productName("GOWUJI Macro Pad");
  USB.manufacturerName("GOWUJI DIY");
  USB.usbPower(500);
  keyboard.begin();
  consolePort.begin(115200);
  consolePort.setTxTimeoutMs(2);  // Do not let a stalled host block matrix scans for 250 ms.
  USB.begin();
  if (wireless) BleKeys::start();
  uint64_t total = 0;
  for (uint8_t i=0;i<24;i++) {
    total += touchRead(TOUCH_PIN);
    delay(6);
  }
  touchBaseline = total / 24;
  pixels.show();  // First update after the separate LED rail has ramped.
  uint32_t now = millis();
  for (auto &k: key) k.changed = now;
}

void loop() {
  uint32_t now=millis();
  bool bleReady = wireless && BleKeys::authenticated.load();
  if (bleWasReady!=bleReady) {
    hidClear();
    bleWasReady=bleReady;
  }
  if (dialTap && now-dialAt>=28) { hidRelease(dialTap); dialTap=0; }
  serialInput(now);
  if (now-lastScan>=1) {
    lastScan=now;
    readMatrix(now);
    readEncoder();
  }
  if (now-lastTouch>=12) { lastTouch=now; readTouch(now); }
  if (now-lastDisplay>=25) { lastDisplay=now; display(now); }
  delayMicroseconds(125);
}
