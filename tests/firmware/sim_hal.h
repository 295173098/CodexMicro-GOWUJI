#pragma once
#include <array>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <string>
#include <vector>
#include "pins.h"

constexpr int LOW=0, HIGH=1, INPUT=0, OUTPUT=1, INPUT_PULLUP=2;
constexpr int NEO_GRB=0, NEO_KHZ800=0;
static uint64_t sim_us=0, output_since=0;
static uint32_t sim_touch=1000;
static int sim_rotary=3;
static std::array<bool,19> contacts{};
static std::array<int,49> mode{}, latch{};
static int active_row=-1;
inline uint32_t millis() { return uint32_t(sim_us/1000); }
inline void delayMicroseconds(uint32_t us) { sim_us+=us; }
inline void delay(uint32_t ms) { delayMicroseconds(ms*1000); }
inline uint32_t touchRead(int pin) { assert(pin==TOUCH_PIN); return sim_touch; }
inline void digitalWrite(int pin,int level) { latch[pin]=level; }
inline void pinMode(int pin,int next) {
  mode[pin]=next;
  for (int r=0;r<4;r++) if (ROWS[r]==pin) {
    if (next==OUTPUT) {
      assert(active_row==-1 && latch[pin]==LOW);
      active_row=r;
      output_since=sim_us;
    } else if (active_row==r) active_row=-1;
  }
}
inline int digitalRead(int pin) {
  if (pin==ENC_A) return (sim_rotary>>1)&1;
  if (pin==ENC_B) return sim_rotary&1;
  for (int c=0;c<5;c++) if (COLS[c]==pin && active_row>=0) {
    assert(sim_us-output_since>=25);
    int key=MATRIX[active_row][c];
    return (key>=0 && contacts[key]) ? LOW : HIGH;
  }
  return HIGH;
}

struct USBFake {
  void productName(const char*) {}
  void manufacturerName(const char*) {}
  void usbPower(int ma) { assert(ma==500); }
  void begin() {}
};
static USBFake USB;
struct USBCDC {
  bool connected=true;
  std::deque<char> rx;
  std::string tx;
  void begin(int baud) { assert(baud==115200); }
  void setTxTimeoutMs(int ms) { assert(ms<=3); }
  explicit operator bool() const { return connected; }
  int available() const { return connected ? int(rx.size()) : 0; }
  int read() { int c=rx.front(); rx.pop_front(); return c; }
  void println(const char* str) { tx+=str; tx+="\r\n"; }
  void printf(const char* fmt,...) {
    char b[100];
    va_list args;
    va_start(args,fmt);
    std::vsnprintf(b,sizeof(b),fmt,args);
    va_end(args);
    tx+=b;
  }
  void inject(std::string s) { for (char c:s) rx.push_back(c); }
};
struct USBHIDKeyboard {
  std::vector<int> events;
  void begin() {}
  int pressRaw(int key) { events.push_back(key); return 1; }
  int releaseRaw(int key) { events.push_back(-key); return 1; }
  void releaseAll() { events.push_back(0); }
};
namespace BleKeys {
  struct Flag { bool enabled=false; bool load() const { return enabled; } };
  static Flag authenticated;
  static bool started=false;
  static USBHIDKeyboard fake;
  inline void start() { started=true; }
  inline bool press(uint8_t usage) { return authenticated.enabled && fake.pressRaw(usage); }
  inline void release(uint8_t usage) { fake.releaseRaw(usage); }
  inline void clear() { fake.releaseAll(); }
}
struct Adafruit_NeoPixel {
  std::array<uint32_t,6> state{};
  uint32_t updates=0;
  Adafruit_NeoPixel(int n,int pin,int) { assert(n==6 && pin==RGB_PIN); }
  void begin() {}
  void setBrightness(int max) { assert(max<=45); }
  void clear() { state.fill(0); }
  void show() { assert(millis()>=100); updates++; }
  void setPixelColor(int i,uint32_t c) { state.at(i)=c; }
};
