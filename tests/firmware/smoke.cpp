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
    consolePort.inject("HELLO GOWUJI/1\nMIC ON\n"); run(5);
    contacts[PTT_PRIMARY]=true; run(60);
    has("EV MIC_READY 0");
    has_not("EV MIC_BEGIN");
    assert(!MicInput::active);
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
  consolePort.inject("MIC ON\n"); run(50);
  has("EV MIC_READY 1"); has_not("EV MIC_BEGIN"); has_not("AUD ");
  assert(!MicInput::active);
  consolePort.tx.clear();
  contacts[PTT_SECONDARY]=true; run(12);
  contacts[PTT_PRIMARY]=false; run(12);
  has_not("EV PTT "); has_not("EV PTT_B");
  consolePort.inject("HELLO GOWUJI/1\n"); run(2);
  has("EV PTT_STATE 1");
  contacts[PTT_SECONDARY]=false; run(12);
  has("EV PTT 0");
  consolePort.tx.clear();
  contacts[PTT_SECONDARY]=true; run(51);
  has("EV PTT 1"); has_not("EV PROFILE ");
  has("EV MIC_BEGIN 1\nAUD 0 EhIS");
  const auto audio=consolePort.tx.find("AUD 0 ");
  assert(consolePort.tx.find('\n',audio)-audio==434);
  assert(MicInput::active);
  contacts[PTT_SECONDARY]=false; run(12);
  has("EV PTT 0");
  has("EV MIC_END 1\n");
  assert(!MicInput::active);
  const size_t afterRelease=consolePort.tx.size();
  run(30);
  assert(consolePort.tx.size()==afterRelease);
  consolePort.tx.clear();
  contacts[PTT_PRIMARY]=true; run(30);
  consolePort.tx_room=0; run(55);
  assert(!MicInput::active);
  consolePort.tx_room=64; run(10);
  has("EV MIC_END 0");
  contacts[PTT_PRIMARY]=false; run(12);
  contacts[PTT_PRIMARY]=true; run(45);
  assert(MicInput::active);
  consolePort.connected=false; run(2);
  assert(!MicInput::active);
  consolePort.connected=true;
  contacts[PTT_PRIMARY]=false; run(12);
  consolePort.inject("HELLO GOWUJI/1\nMIC ON\n"); run(4);
  contacts[PTT_PRIMARY]=true; run(45);
  assert(MicInput::active);
  run(2501);
  assert(!MicInput::active);
  consolePort.inject("HELLO GOWUJI/1\nMIC ON\n"); run(45);
  assert(!MicInput::active);  // Re-subscription while held does not restart capture.
  contacts[PTT_PRIMARY]=false; run(12);
  consolePort.tx.clear();
  contacts[PTT_PRIMARY]=true; run(45);
  for (int i=0;i<61;i++) {
    consolePort.inject("HELLO GOWUJI/1\nMIC ON\n");
    run(1000);
  }
  assert(!MicInput::active);
  has("EV MIC_END 1\n");
  contacts[PTT_PRIMARY]=false; run(12);
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
  std::cout<<"Matrix, USB lease, LED parser, dual-contact PTT, encoder, touch and gated USB audio: pass\n";
}
