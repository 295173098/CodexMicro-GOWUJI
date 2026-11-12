"""Audit fabricated geometry and bound DC copper drop. Run with KiCad's Python."""
import argparse
from collections import defaultdict
import heapq
import json
import math
from pathlib import Path

import pcbnew as p
from design import MIC

F, B = p.F_Cu, p.B_Cu
COPPER_OHM_SQUARE = 0.00065  # conservative hot 1 oz / 35 µm copper


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    b=p.LoadBoard(str(args.board))
    tracks=list(b.GetTracks())
    vias=[t for t in tracks if isinstance(t,p.PCB_VIA)]
    lines=[t for t in tracks if not isinstance(t,p.PCB_VIA)]
    min_trace=min(p.ToMM(t.GetWidth()) for t in lines)
    min_via=min(p.ToMM(t.GetDrillValue()) for t in vias)
    min_ring=min(p.ToMM(t.GetWidth(F)-t.GetDrillValue())/2 for t in vias)
    assert min_trace>=.15 and min_via>=.30 and min_ring>=.15
    # Restrict the smaller 0.15 mm tracks to the MEMS ground ring breakout.
    for t in lines:
        if p.ToMM(t.GetWidth()) < .20:
            assert t.GetNetname() in ("/PDM_CLK","/PDM_DATA","/V3V3")
            for point in (t.GetStart(),t.GetEnd()):
                assert abs(p.ToMM(point.x)-MIC[0]) <= 2 and abs(p.ToMM(point.y)-MIC[1]) <= 2.4
    graph=defaultdict(list)
    pads={}

    def node(net,xy,layer):
        return (net,xy.x,xy.y,layer)
    def link(a,c,r):
        graph[a].append((c,r))
        graph[c].append((a,r))
    for t in lines:
        n,layer=t.GetNetname(),t.GetLayer()
        link(node(n,t.GetStart(),layer),node(n,t.GetEnd(),layer),
             COPPER_OHM_SQUARE*t.GetLength()/t.GetWidth())
    for t in vias:
        n,xy=t.GetNetname(),t.GetPosition()
        link(node(n,xy,F),node(n,xy,B),.003)
    track_nodes=list(graph)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            net=pad.GetNetname()
            if not net: continue
            terminal=(fp.GetReference(),pad.GetNumber())
            pads[terminal]=terminal
            for n,x,y,layer in track_nodes:
                if n==net and pad.IsOnLayer(layer) and pad.HitTest(p.VECTOR2I(x,y)):
                    dist=p.ToMM(round(math.hypot(x-pad.GetPosition().x,y-pad.GetPosition().y)))
                    link(terminal,(n,x,y,layer),.001+.002*dist)

    def resistance(source,target):
        q=[(0.,str(source),source)]
        best={}
        while q:
            r,_,a=heapq.heappop(q)
            if a in best: continue
            best[a]=r
            if a==target: return r
            for c,w in graph[a]:
                if c not in best: heapq.heappush(q,(r+w,str(c),c))
        raise RuntimeError(f"No copper path {source} -> {target}")

    vin=resistance(("U1","5V"),("U3","1"))
    pixels=[]
    for i in range(1,7):
        led=f"LED{i}"
        pixels.append({"ref":led,
            "vbus_to_switch_ohm":vin,
            "switch_to_led_ohm":resistance(("U3","6"),(led,"1")),
            "led_to_connector_gnd_ohm":resistance((led,"3"),("U1","GND"))})
    max_loop=max(sum(row[k] for k in row if k.endswith("_ohm")) for row in pixels)
    data=dict(min_trace_mm=min_trace,min_via_drill_mm=min_via,min_via_ring_mm=min_ring,
              traces=len(lines),vias=len(vias),max_path_loop_ohm=max_loop,led_paths=pixels)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,indent=2))


if __name__=="__main__":
    main()
