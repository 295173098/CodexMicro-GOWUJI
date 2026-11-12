"""GOWUJI companion: local USB CDC and the Codex CLI app-server over stdio."""
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time


class AppServer:
    def __init__(self, messages, cwd):
        executable = (shutil.which("codex.cmd") if os.name == "nt" else None) or shutil.which("codex")
        if executable is None:
            raise RuntimeError("Install Codex CLI and sign in before launching the companion.")
        self.messages = messages
        self.process = subprocess.Popen(
            [executable, "app-server"], cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.next_id = 0
        threading.Thread(target=self.receive, daemon=True).start()

    def write(self, msg):
        self.process.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def request(self, method, params=None):
        self.next_id += 1
        msg = dict(id=self.next_id, method=method)
        if params is not None:
            msg["params"] = params
        self.write(msg)
        return self.next_id

    def initialize(self):
        return self.request("initialize", {"clientInfo": {
            "name": "gowuji", "title": "GOWUJI Macro Pad", "version": "0.1.0"}})

    def receive(self):
        for line in self.process.stdout:
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    self.messages.put(("rpc", value))
            except json.JSONDecodeError:
                pass
        self.messages.put(("info", "Codex App Server disconnected."))

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()


def decode_event(line):
    profile = re.fullmatch(r"EV PROFILE ([0-5])",line)
    if profile:
        return "PROFILE",int(profile[1])
    match = re.fullmatch(r"EV ([A-Z0-9_]+) (-?1|0)", line)
    return (match[1], int(match[2])) if match else None


def decode_audio(line):
    match = re.fullmatch(r"AUD ([0-9]{1,4}) ([A-Za-z0-9+/]{427}=)", line)
    if match:
        try:
            pcm = base64.b64decode(match[2], validate=True)
        except binascii.Error:
            return None
        if len(pcm) == 320 and int(match[1]) < 6000:
            return int(match[1]), pcm
    return None


class Device:
    def __init__(self, port, messages, board_mic=False):
        import serial
        self.port = serial.Serial(port, 115200, timeout=.10, write_timeout=.25)
        self.messages = messages
        self.leds = "000000"
        self.board_mic = board_mic
        self.stop = threading.Event()
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            ready = False
            due = hello_at = 0.0
            line = bytearray()
            overflow = False
            supported = False
            awaiting_mic = 0.0
            while not self.stop.is_set():
                now = time.monotonic()
                if now >= hello_at:
                    self.port.write(b"HELLO GOWUJI/1\n" + (b"MIC ON\n" if self.board_mic else b""))
                    hello_at = now + 1.0
                if ready and now >= due:
                    self.port.write(f"LED {self.leds}\n".encode())
                    due = now + .45
                chunk = self.port.read(self.port.in_waiting or 1)
                for b in chunk:
                    if b == 10:
                        s = "" if overflow else line.decode("ascii", "replace").strip()
                        line.clear()
                        overflow = False
                        if s == "OK GOWUJI/1" and not ready:
                            ready = True
                            awaiting_mic = now + 2 if self.board_mic else 0
                            self.messages.put(("info","GOWUJI USB connected."))
                        elif ready and (event := decode_event(s)):
                            if event[0] == "MIC_READY":
                                supported = True
                            self.messages.put(("key",event))
                        elif ready and self.board_mic and s.startswith("AUD "):
                            self.messages.put(("audio",decode_audio(s)))
                    elif len(line) < 448 and not overflow:
                        line.append(b)
                    else:
                        overflow = True
                if awaiting_mic and now >= awaiting_mic:
                    if not supported:
                        self.messages.put(("info","No board microphone detected. For Rev A3, restart with --mic computer."))
                    awaiting_mic = 0
        except OSError as exc:
            self.messages.put(("usb_lost",f"USB disconnected: {exc}"))
        finally:
            self.port.close()


COLORS = ["#6d737b","#eee9e2","#3e7eff","#2cb978","#edaa32","#e84862"]
PROMPTS = {
    "JOY_UP": "Review the current changes for correctness and missing tests. Report actionable findings.",
    "JOY_RIGHT": "Investigate the error I describe and identify its cause: ",
    "JOY_DOWN": "Suggest a small refactor that preserves the current behavior: ",
    "JOY_LEFT": "Explain the relevant code path and how to verify it: ",
}
APPROVALS = {"item/commandExecution/requestApproval","item/fileChange/requestApproval"}
REMAPPABLE = {*PROMPTS,"NEW_CHAT","FIND","DIAL_PUSH","JOY_CENTER"}
PROFILE_ACTIONS = {"NONE","NEW_CHAT","FIND","DIAL_PUSH","JOY_CENTER"}


def load_profiles(path):
    profiles = [{} for _ in range(6)]
    if path is None:
        return profiles
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,list) or not 1 <= len(data) <= 6:
        raise ValueError("Profiles must be a JSON array of one to six objects.")
    for i, layer in enumerate(data):
        if not isinstance(layer,dict) or set(layer) - REMAPPABLE:
            raise ValueError(f"Profile {i+1}: unsupported key name.")
        for key, action in layer.items():
            if isinstance(action,str) and action in PROFILE_ACTIONS:
                continue
            if not (isinstance(action,dict) and set(action)=={"prompt"} and
                    isinstance(action["prompt"],str) and 0<len(action["prompt"])<=1500):
                raise ValueError(f"Profile {i+1}, {key}: expected a supported action or a prompt.")
        profiles[i] = layer
    return profiles


def state_led(status, previous=1):
    if not isinstance(status, dict):
        return previous
    match status.get("type"):
        case "active":
            return 4 if status.get("activeFlags") else 2
        case "systemError":
            return 5
        case "idle" | "notLoaded":
            return previous if previous in (3,5) else 1
        case _:
            return previous


class Voice:
    def __init__(self, model, messages, source):
        import vosk
        self.source, self.vosk = source, vosk
        if source == "computer":
            import sounddevice
            self.sd = sounddevice
        self.model = vosk.Model(str(model))
        self.messages = messages
        self.stream = None
        self.recording = False

    def begin(self, slot):
        if self.recording:
            return
        self.frames, self.invalid = [], False
        self.slot = slot
        if self.source == "board":
            self.recording = True
            return
        def capture(data, *_):
            if len(self.frames) < 600:
                self.frames.append(bytes(data))
        self.stream = self.sd.RawInputStream(samplerate=16000, channels=1, dtype="int16",
                                             blocksize=1600, callback=capture)
        try:
            self.stream.start()
        except Exception:
            self.cancel()
            raise
        self.recording = True

    def feed(self, packet):
        if not self.recording or self.source != "board" or self.invalid:
            return
        if packet is None or packet[0] != len(self.frames) or len(self.frames) >= 6000:
            self.invalid = True
            return
        self.frames.append(packet[1])

    def cancel(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        self.recording = False
        self.frames = []

    def end(self, complete=True):
        if not self.recording:
            return
        frames, slot = self.frames, self.slot
        valid = complete and not self.invalid
        self.cancel()
        if not valid or not frames:
            self.messages.put(("info","Audio was interrupted." if not valid else "Hold the voice key while speaking."))
            return
        def decode():
            rec = self.vosk.KaldiRecognizer(self.model,16000)
            texts = []
            for chunk in frames:
                if rec.AcceptWaveform(chunk):
                    texts.append(json.loads(rec.Result()).get("text",""))
            texts.append(json.loads(rec.FinalResult()).get("text",""))
            self.messages.put(("voice",(slot," ".join(t for t in texts if t))))
        threading.Thread(target=decode,daemon=True).start()


class Window:
    def __init__(self, opts):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root = tk.Tk()
        self.root.title("GOWUJI · Codex companion")
        self.root.geometry("850x570")
        self.cwd = str(Path(opts.cwd).resolve())
        self.inbox = queue.Queue()
        self.device = self.rpc = self.voice = None
        self.rpc_ready = False
        self.pending = {}
        self.approvals = {}
        self.turns = {}
        self.starting = set()
        self.slots = [None]*6
        self.slot_labels = [""]*6
        self.transcript = [""]*6
        self.drafts = [""]*6
        self.leds = [0]*6
        self.selected = 0
        self.model = None
        self.efforts = ["default"]
        self.effort = 0
        self.effort_label = tk.StringVar(value="Effort: default")
        self.status = tk.StringVar(value=f"Workspace: {self.cwd}")
        self.approval_label = tk.StringVar(value="")
        self.demo = opts.demo
        self.profile = 0
        self.profiles = load_profiles(opts.profiles)
        frame = ttk.Frame(self.root,padding=12)
        frame.pack(fill="both",expand=True)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        self.buttons = []
        for i in range(6):
            button = tk.Button(top,text=f"{i+1} · Empty",command=lambda j=i:self.select(j),width=14)
            button.pack(side="left",fill="x",expand=True,padx=1)
            self.buttons.append(button)
        controls = ttk.Frame(frame)
        controls.pack(fill="x",pady=6)
        for label, event in [("New","NEW_CHAT"),("Find / assign","FIND"),("Cancel turn","INTERRUPT"),
                             ("Accept","ACCEPT"),("Decline","DECLINE")]:
            ttk.Button(controls,text=label,command=lambda e=event:self.key(e,1)).pack(side="left")
        ttk.Label(controls,textvariable=self.effort_label).pack(side="right")
        self.log = tk.Text(frame,wrap="word",state="disabled",height=15)
        self.log.pack(fill="both",expand=True)
        ttk.Label(frame,textvariable=self.approval_label,wraplength=810).pack(fill="x")
        self.entry = tk.Text(frame,wrap="word",height=4)
        self.entry.pack(fill="x",pady=(6,0))
        ttk.Button(frame,text="Send prompt",command=self.send).pack(anchor="e",pady=4)
        ttk.Label(frame,textvariable=self.status,wraplength=810).pack(fill="x")
        if opts.voice_model:
            try: self.voice = Voice(opts.voice_model,self.inbox,opts.mic)
            except Exception as exc: self.status.set(f"Voice: {exc}")
        if opts.port:
            try: self.device = Device(opts.port,self.inbox,bool(self.voice and opts.mic == "board"))
            except Exception as exc: self.status.set(f"USB: {exc}")
        if not opts.demo:
            try:
                self.rpc = AppServer(self.inbox,self.cwd)
                self.pending[self.rpc.initialize()] = self.initialized
            except (OSError,RuntimeError) as exc:
                self.status.set(str(exc))
        else:
            self.slot_labels = ["Idle","Running","Done","Waiting","Error",""]
            self.leds = [1,2,3,4,5,0]
        self.refresh()
        self.root.after(40,self.tick)
        self.root.protocol("WM_DELETE_WINDOW",self.close)

    def rpc_call(self, method, args, callback=lambda result:None):
        if not self.rpc_ready:
            self.status.set("Codex App Server is not ready.")
            return
        try:
            self.pending[self.rpc.request(method,args)] = callback
        except (OSError, ValueError) as exc:
            self.status.set(f"Codex: {exc}")

    def initialized(self, _):
        self.rpc.write({"method":"initialized"})
        self.rpc_ready = True
        self.status.set(f"Codex connected · {self.cwd}")
        def apply(data):
            models = data.get("data",[])
            model = next((m for m in models if m.get("isDefault")),None)
            if model:
                self.model = model.get("id") or model.get("model")
                self.efforts += [e["reasoningEffort"] for e in model.get("supportedReasoningEfforts",[])
                                 if e.get("reasoningEffort")]
        self.rpc_call("model/list",{"limit":100},apply)

    def idx(self, thread):
        return self.slots.index(thread) if thread and thread in self.slots else None

    def append(self, i, text):
        self.transcript[i] = (self.transcript[i] + text)[-120000:]
        if i == self.selected:
            self.draw_log()

    def draw_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0","end")
        self.log.insert("end",self.transcript[self.selected])
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh(self):
        for i,b in enumerate(self.buttons):
            b.configure(text=f"{i+1} · {self.slot_labels[i][:10] or 'Empty'}",bg=COLORS[self.leds[i]],
                        relief="sunken" if i == self.selected else "raised")
        thread = self.slots[self.selected]
        waiting = next((p for p in self.approvals.values() if p.get("threadId")==thread),None)
        self.approval_label.set(("Pending approval: "+str(waiting.get("command") or waiting.get("reason") or
                                  waiting.get("grantRoot") or "file change (details not provided)")) if waiting else "")
        self.effort_label.set(f"Effort: {self.efforts[self.effort]}")
        if self.device:
            self.device.leds = "".join(map(str,self.leds))

    def select(self,i):
        self.drafts[self.selected] = self.entry.get("1.0","end-1c")
        self.selected = i
        self.entry.delete("1.0","end")
        self.entry.insert("1.0",self.drafts[i])
        self.entry.focus_set()
        self.draw_log()
        self.refresh()

    def assign(self, i, thread):
        tid = thread["id"]
        other = self.idx(tid)
        if other is not None and other != i:
            self.select(other)
            return
        if self.slots[i] != tid:
            self.transcript[i] = ""
        self.slots[i] = tid
        self.slot_labels[i] = thread.get("name") or thread.get("preview") or "Chat"
        self.leds[i] = state_led(thread.get("status"))
        self.select(i)

    def new(self, i):
        self.rpc_call("thread/start",{"cwd":self.cwd,"approvalPolicy":"on-request","sandbox":"workspace-write"},
                      lambda r:self.assign(i,r["thread"]))

    def find(self):
        slot = self.selected
        def picker(response):
            rows = [t for t in response.get("data",[]) if not t.get("ephemeral")]
            dialog = self.tk.Toplevel(self.root)
            dialog.title(f"Assign to slot {slot+1}")
            listing = self.tk.Listbox(dialog,width=82,height=16)
            listing.pack(fill="both",expand=True)
            for thread in rows:
                listing.insert("end",thread.get("name") or thread.get("preview") or thread["id"])
            def choose(_=None):
                sel = listing.curselection()
                if not sel: return
                t = rows[sel[0]]
                dialog.destroy()
                self.rpc_call("thread/resume",{"threadId":t["id"],"approvalPolicy":"on-request",
                                              "sandbox":"workspace-write","cwd":self.cwd},
                              lambda r:self.assign(slot,r["thread"]))
            listing.bind("<Double-Button-1>",choose)
            self.ttk.Button(dialog,text="Assign",command=choose).pack()
        self.rpc_call("thread/list",{"limit":40,"cwd":self.cwd,"sourceKinds":["cli","vscode","appServer"]},picker)

    def send(self):
        i = self.selected
        tid = self.slots[i]
        text = self.entry.get("1.0","end-1c").strip()
        if not self.rpc_ready or not tid or not text or tid in self.turns or tid in self.starting:
            self.status.set("Assign a chat and enter a prompt; wait for any active turn to finish.")
            return
        params = {"threadId":tid,"input":[{"type":"text","text":text}],"approvalPolicy":"on-request"}
        if self.effort:
            params.update(model=self.model,effort=self.efforts[self.effort])
        self.starting.add(tid)
        def sent(_):
            self.starting.discard(tid)
            self.append(i,"\nYou: "+text+"\nCodex: ")
            if self.selected == i and self.entry.get("1.0","end-1c").strip() == text:
                self.entry.delete("1.0","end")
            elif self.drafts[i].strip() == text:
                self.drafts[i] = ""
        sent.failed = lambda: self.starting.discard(tid)
        self.rpc_call("turn/start",params,sent)

    def key(self, name, value):
        if name == "PROFILE":
            if value != self.profile:
                self.profile = value
                self.status.set(f"Keypad profile {self.profile+1}")
            return
        if name == "PTT_STATE":
            # Reconcile a lost release packet; a heartbeat can never start recording.
            if not value and self.voice and self.voice.recording:
                self.voice.end(complete=self.voice.source == "computer")
            return
        if name.startswith("MIC_"):
            if self.voice and self.voice.source == "board":
                if name == "MIC_BEGIN" and value:
                    self.voice.cancel()
                    self.voice.begin(self.selected)
                    self.status.set("Recording from GOWUJI…")
                elif name == "MIC_END":
                    self.voice.end(complete=bool(value))
                    self.status.set("Transcribing locally…" if value else "Board microphone recording interrupted.")
                elif name == "MIC_READY" and not value:
                    self.status.set("Board microphone needs USB mode. Restart without holding the dial.")
                elif name == "MIC_ERROR":
                    self.status.set("Board microphone did not start.")
            return
        if name == "PTT":
            if self.voice and self.voice.source == "computer":
                try: self.voice.begin(self.selected) if value else self.voice.end()
                except Exception as exc: self.status.set(f"Microphone: {exc}")
            elif not self.voice and value:
                self.status.set("Push to talk needs --voice-model. You can type a prompt below.")
            return
        if not value: return
        remap = self.profiles[self.profile].get(name)
        if isinstance(remap,dict):
            self.insert_prompt(remap["prompt"])
            return
        if isinstance(remap,str):
            name=remap
        if name == "DIAL":
            self.effort = min(len(self.efforts)-1,max(0,self.effort+value))
            self.refresh()
        elif name == "DIAL_PUSH":
            self.effort=0
            self.refresh()
        elif name.startswith("SLOT") and name[-1:] in "123456" and len(name)==5:
            self.select(int(name[-1])-1)
        elif name == "NEW_CHAT":
            free = next((i for i,s in enumerate(self.slots) if s is None),self.selected)
            self.new(free)
        elif name == "FIND":
            self.find()
        elif name in PROMPTS:
            self.insert_prompt(PROMPTS[name])
        elif name == "JOY_CENTER":
            self.entry.focus_set()
        elif name == "INTERRUPT":
            tid = self.slots[self.selected]
            if tid in self.turns:
                self.rpc_call("turn/interrupt",{"threadId":tid,"turnId":self.turns[tid]})
        elif name in ("ACCEPT","DECLINE"):
            tid = self.slots[self.selected]
            for req,p in self.approvals.items():
                if p.get("threadId")==tid:
                    choice = "accept" if name == "ACCEPT" else "decline"
                    available = p.get("availableDecisions")
                    if available and choice not in available:
                        self.status.set("This decision is not available for the pending request.")
                        return
                    self.rpc.write({"id":req,"result":{"decision":choice}})
                    del self.approvals[req]
                    self.refresh()
                    break

    def insert_prompt(self, text):
        self.entry.insert("end",(" " if self.entry.get("1.0","end-1c") else "")+text)
        self.entry.focus_set()

    def rpc_event(self, m):
        method, p, req = m.get("method"), m.get("params",{}), m.get("id")
        if not method and req in self.pending:
            callback = self.pending.pop(req)
            if "error" in m:
                self.status.set(str(m["error"].get("message","Codex request failed.")))
                if hasattr(callback,"failed"):
                    callback.failed()
            else:
                callback(m.get("result",{}))
            return
        tid = p.get("threadId")
        i = self.idx(tid)
        if req is not None and method:
            if method in APPROVALS:
                self.approvals[req] = p
                if i is not None: self.leds[i]=4
            else:
                self.rpc.write({"id":req,"error":{"code":-32601,"message":"Request not supported by GOWUJI."}})
                self.status.set(f"Unsupported Codex request: {method}")
        elif method == "serverRequest/resolved":
            self.approvals.pop(p.get("requestId"),None)
        elif i is not None:
            if method == "thread/status/changed":
                self.leds[i] = state_led(p.get("status"),self.leds[i])
            elif method == "turn/started":
                self.turns[tid] = p["turn"]["id"]
                self.leds[i] = 2
            elif method == "turn/completed":
                self.turns.pop(tid,None)
                status = p["turn"]["status"]
                self.leds[i] = {"completed":3,"failed":5}.get(status,1)
                self.append(i,f"\n[{status}]\n")
            elif method == "item/agentMessage/delta":
                self.append(i,p.get("delta",""))
        self.refresh()

    def tick(self):
        for _ in range(80):
            try: kind,arg = self.inbox.get_nowait()
            except queue.Empty: break
            try:
                if kind=="rpc": self.rpc_event(arg)
                elif kind=="key": self.key(*arg)
                elif kind=="info": self.status.set(arg)
                elif kind=="usb_lost":
                    if self.voice: self.voice.cancel()
                    self.status.set(arg)
                elif kind=="audio":
                    if self.voice: self.voice.feed(arg)
                elif kind=="voice":
                    i,text=arg
                    self.status.set("Transcription added to draft." if text else "No speech recognized.")
                    if not text: continue
                    if i==self.selected: self.entry.insert("end"," "+text)
                    else: self.drafts[i] += " "+text
            except Exception as exc:
                self.status.set(f"{kind}: {exc}")
        self.root.after(40,self.tick)

    def close(self):
        if self.device: self.device.stop.set()
        if self.voice: self.voice.cancel()
        if self.rpc: self.rpc.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",help="USB CDC port, e.g. COM6 or /dev/cu.usbmodem1101")
    parser.add_argument("--cwd",default=os.getcwd(),help="Project directory for Codex")
    parser.add_argument("--voice-model",type=Path,help="Local Vosk model folder")
    parser.add_argument("--mic",choices=("board","computer"),default="board",help="Voice source (default: Rev A4 board microphone)")
    parser.add_argument("--profiles",type=Path,help="JSON map for up to six touch-selectable profiles")
    parser.add_argument("--demo",action="store_true",help="Simulate six LED states; no Codex requests")
    parser.add_argument("--check-cli",action="store_true",help="Check local app-server handshake without starting a chat")
    args=parser.parse_args()
    if args.check_cli:
        messages=queue.Queue()
        app=AppServer(messages,args.cwd)
        try:
            ident=app.initialize()
            kind,data=messages.get(timeout=12)
            if kind!="rpc" or data.get("id")!=ident or "result" not in data:
                raise RuntimeError(f"Unexpected initialize response: {data}")
            app.write({"method":"initialized"})
            print("Codex App Server initialization passed.")
        finally:
            app.close()
        return
    Window(args).root.mainloop()


if __name__=="__main__":
    main()
