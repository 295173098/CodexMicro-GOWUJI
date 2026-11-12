// Compile the production sketch with the deterministic host-side hardware boundary.
#define GOWUJI_HOST_SIM
#include "Gowuji.ino"
#include <iostream>

void run(unsigned ms) {
  auto stop=sim_us+1000*ms;
  while (sim_us<stop) loop();
  assert(active_row==-1);
}
void has(const char* text) { assert(consolePort.tx.find(text)!=std::string::npos); }
void has_not(const char* text) { assert(consolePort.tx.find(text)==std::string::npos); }

int main(int argc,char**) {
  bool ble=argc>1;
  contacts[ble?13:3]=true;
  setup();
  run(24);
  assert(BleKeys::started==ble && keyboard.events.empty());
  contacts.fill(false);
  run(24);
  if (ble) {
    BleKeys::authenticated.enabled=true;
    run(2);
    contacts[0]=true;
    run(12);
    assert(BleKeys::fake.events.back()==0x68);
    BleKeys::authenticated.enabled=false;
    run(4);
    assert(BleKeys::fake.events.back()==0);
    contacts[0]=false;
    run(12);
    std::cout<<"BLE selection and disconnect: pass\n";
    return 0;
  }
  assert(keyboard.events.empty());
  // Bounce shorter than debounce must not reach the host.
  contacts[0]=true; run(3);
  contacts[0]=false; run(4);
  assert(keyboard.events.empty());
  contacts[0]=true; run(11);
  assert(keyboard.events.back()==0x68);
  consolePort.inject("HELLO GOWUJI/1\r\n"); run(3);
  has("OK GOWUJI/1"); has("EV PROFILE 0"); has("EV PTT_STATE 0");
  assert(keyboard.events.back()==0);
  contacts[0]=false; run(12);
  consolePort.tx.clear();
  contacts[3]=true;
  contacts[14]=true;
  contacts[16]=true;
  run(12);
  has("EV PTT 1"); has("EV JOY_UP 1"); has("EV JOY_DOWN 1");
  has_not("EV JOY_RIGHT 1");
  consolePort.inject("HELLO GOWUJI/1\n"); run(2);
  has("EV PTT_STATE 1");
  contacts[3]=false; run(12);
  has("EV PTT 0");
  consolePort.inject("HELLO GOWUJI/1\nLED 123456\n"); run(30);
  assert(remoteLED[0]==1 && remoteLED[5]==6);
  consolePort.inject("LED 987654\n"+std::string(70,'X')+"HELLO GOWUJI/1\n");
  run(3);
  assert(remoteLED[0]==1 && remoteLED[5]==6);
  sim_rotary=2; run(3);
  sim_rotary=0; run(3);
  has("EV DIAL -1");
  sim_rotary=2; run(3);
  sim_rotary=3; run(3);
  has("EV DIAL 1");
  sim_touch=1400; run(50);
  has("EV TOUCH 1"); has("EV PROFILE 1");
  sim_touch=1000; run(50);
  has("EV TOUCH 0");
  run(2501);
  contacts[1]=true; run(12);
  assert(keyboard.events.back()==0x69 && pixels.updates>1);
  contacts[1]=false; run(12);
  assert(keyboard.events.back()==-0x69);
  std::cout<<"Matrix bounce, chords, USB lease, LED parser, PTT heartbeat, encoder and touch: pass\n";
}
