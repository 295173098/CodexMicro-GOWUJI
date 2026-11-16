"""Seed Rev B critical copper on an unrouted placement. Use KiCad 9 Python."""
import argparse
import re
from pathlib import Path

import pcbnew as k

F, I1, I2, B = k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu


def point(x, y):
    return k.VECTOR2I(k.FromMM(x), k.FromMM(y))


def seed(board):
    if list(board.GetTracks()) or list(board.Zones()):
        raise ValueError("Expected the unrouted Rev B placement")
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    nets = board.GetNetsByName()

    def move(ref, x, y, angle=0):
        f = footprints[ref]
        f.SetPosition(point(x, y))
        f.SetOrientationDegrees(angle)

    def xy(p):
        if isinstance(p[0], str):
            ref, number = p
            return footprints[ref].FindPadByNumber(number).GetPosition()
        return point(*p)

    def wire(net, *points, width=.18, layer=F):
        for a, b in zip(points, points[1:]):
            start, end = xy(a), xy(b)
            if start == end:
                continue
            t = k.PCB_TRACK(board)
            t.SetStart(start)
            t.SetEnd(end)
            t.SetWidth(k.FromMM(width))
            t.SetLayer(layer)
            board.Add(t)
            t.SetNet(nets["/" + net])
            t.SetLocked(True)

    def via(net, at):
        v = k.PCB_VIA(board)
        v.SetPosition(xy(at))
        v.SetViaType(k.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetWidth(k.FromMM(.60))
        v.SetDrill(k.FromMM(.30))
        board.Add(v)
        v.SetNet(nets["/" + net])
        v.SetLocked(True)

    # Type-C reverses the order of the secondary contacts. Split crossings
    # across opposite sides of the connector pad row; use two short B.Cu links.
    move("U6", 32, 11.8, 180)
    move("U5", 37, 18)
    footprints["U5"].Flip(footprints["U5"].GetPosition(), False)
    move("C14", 28.75, 17.3)
    move("C1", 27.3, 20.175)
    move("C15", 43.8, 22.65)
    move("R12", 35.35, 9.65)
    move("R13", 27.8, 9.65, 180)
    move("R10", 50.0, 19.7, 90)
    move("R11", 51.65, 19.7, 90)
    move("C16", 54.0, 19.2)
    move("C26", 52.2, 24.3)
    wire("CC1", ("J2", "A5"), (33.25, 8.05), (34.85, 9.65), ("R12", "1"), width=.16)
    wire("CC2", ("J2", "B5"), (30.25, 8.91), (29.51, 9.65), ("R13", "1"), width=.16)
    for net, pins, exits, transitions in (
        ("USB_P", ("B6", "A6"), ((31.25, 6.23), (32.25, 6.23)), ((31.25, 5.41), (32.25, 5.41))),
        ("USB_N", ("A7", "B7"), ((31.75, 7.74), (32.75, 7.74)), ((31.85, 8.49), (32.75, 8.49))),
    ):
        for pin, exit, via_at in zip(pins, exits, transitions):
            wire(net, ("J2", pin), exit, via_at, width=.16)
            via(net, via_at)
        wire(net, *transitions, width=.18, layer=B)
    wire("USB_P", ("J2", "B6"), (31.25, 8.42), (31.05, 8.62), ("U6", "3"), ("U6", "4"), width=.17)
    wire("USB_N", (32.75, 8.49), (32.95, 8.69), ("U6", "1"), ("U6", "6"), width=.17)

    # Top side USB trunk. Converge the two U6 lines on their south side
    # and reference the main run to In1.Cu.
    wire("USB_P", ("U6", "4"), (31.05, 15.50), (33.45, 17.90), (44.70, 17.90),
         (48.90, 22.10), (51.12, 22.10), (51.65, 21.57), ("R11", "1"), width=.18)
    wire("USB_N", ("U6", "6"), (32.95, 15.08), (34.10, 15.08), (34.65, 15.63), (34.65, 17.05), (35.05, 17.45), (44.88, 17.45),
         (48.78, 21.35), (49.62, 21.35), (50.00, 20.97), ("R10", "1"), width=.18)
    wire("USB_N_MCU", ("U1", "25"), (50.40, 17.6), (50.00, 18.0), ("R10", "2"), width=.17)
    wire("USB_P_MCU", ("U1", "26"), (50.80, 17.6), (51.65, 18.45), ("R11", "2"), width=.17)

    # Crystal on F.Cu, with short branches to each load capacitor.
    move("C17", 44.4, 5.25, 180)
    move("C18", 52.1, 5.55)
    move("C19", 43.35, 7.6, 180)
    move("C23", 41.65, 10.2)
    move("R14", 42.2, 11.65)
    move("C20", 40.3, 7.95, 90)
    move("L1", 43.0, 8.9, 180)
    wire("XTAL_P", ("U1", "54"), (47.2, 8.73), (47.10, 8.63), ("X1", "1"))
    wire("XTAL_P", ("C17", "1"), (45.85, 5.925), (45.85, 6.5), (46.6, 7.25), ("X1", "1"))
    wire("XTAL_N", ("X1", "3"), ("C18", "1"), (51.30, 6.175), (51.30, 7.32),
         (50.17, 8.45), (48.16, 8.45), (47.6, 9.01), ("U1", "53"))

    # RF match and connector, also on F.Cu. Width is provisional pending the
    # fabricator's stackup, including dielectric and copper thickness.
    wire("RF_CHIP", ("U1", "1"), (44.88, 10.4), width=.16)
    wire("RF_CHIP", (44.88, 10.4), (44.88, 10.005), ("L1", "1"), width=.28)
    wire("RF_CHIP", ("C19", "1"), (44.125, 8.55), ("L1", "1"), width=.20)
    wire("RF_FEED", ("J3", "1"), (38.95, 8.27), (39.58, 8.9), (40.3, 8.9),
         ("L1", "2"), width=.28)
    wire("RF_FEED", ("C20", "1"), (40.3, 8.9), width=.18)

    # Ground stitches close to the USB discontinuities, ESD return, RF
    # connector, load capacitors and MCU exposed pad.
    for start, at in [
        (("U6", "2"), (32.0, 9.42)),
        (("R12", "2"), (36.125, 10.85)),
        (("R13", "2"), (26.1, 9.65)),
        (("C17", "2"), (43.625, 4.3)),
        (("C18", "2"), (53.7, 5.55)),
        (("C19", "2"), (42.575, 6.90)),
        (("C20", "2"), (40.3, 6.40)),
        (("C23", "2"), (43.14, 10.2)),
        (("X1", "2"), (48.31, 7.25)),
        (("X1", "4"), (47.1, 4.57)),
        (("J3", "2"), (41.1, 1.2)),
    ]:
        wire("GND", start, at, width=.25)
        via("GND", at)
    for at in [(31.7, 4.43), (32.55, 4.43), (30.42, 8.98), (33.95, 10.9),
               (39.65, 5.25), (38.10, 4.60), (38.2, 7.65)]:
        via("GND", at)
    for x in (47.55, 49, 50.45):
        for y in (11.55, 13, 14.45):
            via("GND", (x, y))

    # Short capacitor feeds and the isolated RF power network.
    wire("VDD_SPI", ("U1", "29"), (53.325, 15.6), ("C24", "1"), width=.18)
    wire("RF_3V3", ("U1", "2"), (44.54, 10.85), (44.34, 11.05), (44.12, 11.05), width=.17)
    wire("RF_3V3", ("U1", "3"), (44.54, 11.23), (44.34, 11.05), width=.17)
    via("RF_3V3", (44.12, 11.05))
    wire("RF_3V3", ("U1", "55"), (46.8, 9.05), (46.38, 8.63), (46.02, 8.63), width=.17)
    wire("RF_3V3", ("U1", "56"), (46.4, 9.0), (46.03, 8.63), width=.17)
    via("RF_3V3", (46.02, 8.63))
    for net, start, points in [
        ("VBUS", ("J2", "A9"), [(29.55, 8.19), (29.32, 8.42)]),
        ("VBUS", ("J2", "A4"), [(34.45, 7.90), (34.75, 8.20)]),
        ("VBUS", ("C14", "1"), [(27.35, 16.15)]),
        ("VBUS", ("U5", "3"), [(40.15, 21.6)]),
        ("V3V3", (40.15, 18.0), [(40.15, 18.75)]),
        ("V3V3", ("C15", "1"), [(42.4, 23.88)]),
        ("LED_5V", ("U3", "6"), [(23.05, 15.60)]),
        ("LED_5V", ("C8", "1"), [(23.60, 23.25)]),
    ]:
        wire(net, start, *points, width=.32, layer=B if start[0]=="U5" or start==(40.15, 18.0) else F)
        via(net, points[-1])


    for ref, pad, target in [
        ("U3", "1", (22.58, 19.94)),
        ("C10", "1", (29.225, 20.15)),
        ("U6", "5", (32.0, 14.05)),
    ]:
        wire("VBUS", (ref, pad), target, width=.28)
        via("VBUS", target)

    wire("VBUS", (29.32, 8.42), (29.32, 11.65), (32.0, 14.33), (32.0, 14.05),
         layer=I2, width=.50)
    wire("VBUS", (34.75, 8.2), (34.75, 11.30), (32.0, 14.05),
         layer=I2, width=.50)
    wire("VBUS", (32.0, 14.33), (29.92, 16.41), (27.61, 16.41), (27.35, 16.15),
         layer=I2, width=.50)
    wire("VBUS", (29.92, 16.41), (29.92, 17.65), (29.225, 18.345), (29.225, 20.15),
         (33.775, 20.15), (35.225, 21.6), (40.15, 21.6),
         layer=I2, width=.50)
    wire("VBUS", (27.35, 16.15), (26.37, 16.15), (22.58, 19.94),
         layer=I2, width=.50)
    wire("V3V3", (40.15, 18.75), (42.4, 21), (42.4, 23.88), layer=I2, width=.50)

    # Microphone's package ground ring blocks direct straight breakout.
    for xdir, ydir, net in ((1, 1, "V3V3"), (-1, -1, "PDM_CLK"), (-1, 1, "PDM_DATA")):
        start, neck, drop = ((13+xdir*x, 11+ydir*y) for x,y in
                             ((.425, .675), (.75, 1.25), (1.80, 2.30)))
        wire(net, start, neck, drop, width=.15)
        via(net, drop)
    wire("GND", (13.425, 10.325), (14.225, 10.325), width=.20)
    for start, end in [((14.225, 11), (14.95, 11)),
                       ((11.775, 11), (11.05, 11)),
                       ((13, 9.275), (13, 8.55)),
                       ((13, 12.725), (13, 13.45))]:
        wire("GND", start, end, width=.32)
        via("GND", end)

    # Place a ground stitch on the LDO input-cap return and the output tab.
    wire("GND", ("U5", "1"), (40.15, 14.75), width=.35, layer=B)
    via("GND", (40.15, 14.75))
    wire("V3V3", (33.85, 18.0), (40.15, 18.0), width=.8, layer=B)


    for layer in (F, I1, I2, B):
        zone = k.ZONE(board)
        zone.SetLayer(layer)
        board.Add(zone)
        zone.SetNet(nets["/GND"])
        zone.SetZoneName("GND reference" if layer in (I1, I2) else "GND outer fill")
        zone.SetLocalClearance(k.FromMM(.22))
        zone.SetMinThickness(k.FromMM(.18))
        zone.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL)
        zone.SetThermalReliefGap(k.FromMM(.25))
        zone.SetThermalReliefSpokeWidth(k.FromMM(.3))
        zone.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        polygon = zone.Outline()
        polygon.NewOutline()
        for x, y in ((.5, .5), (94.5, .5), (94.5, 97.5), (.5, 97.5)):
            polygon.Append(int(k.FromMM(x)), int(k.FromMM(y)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("placement", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dsn", type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.placement.resolve():
        parser.error("Use a different output path")
    board = k.LoadBoard(str(args.placement))
    seed(board)
    if args.dsn:
        board.BuildConnectivity()
        if not k.ExportSpecctraDSN(board, str(args.dsn)):
            raise RuntimeError(f"Could not export {args.dsn}")
        text = args.dsn.read_text(encoding="utf-8")
        text = text.replace("(layer In1.Cu\n      (type signal)",
                            "(layer In1.Cu\n      (type power)")
        # Advertise only In1.Cu to the router as a ground plane.
        text = re.sub(r"\n    \(plane /GND\s*\(polygon (?:F|B|In2)\.Cu[^)]*\)\s*\)", "", text)
        offset = text.index("(class kicad_default")
        tail = text[offset:]
        power = r" /(VBUS|V3V3|LED_5V)(?=\s)"
        tail = re.sub(power, "", tail)
        index = tail.index("\n  )\n  (wiring")
        rules = ('\n    (class gowuji_power /VBUS /V3V3 /LED_5V '
                 '(circuit (use_via "Via[0-3]_600:300_um")) (rule (width 350) (clearance 200)))')
        args.dsn.write_text(text[:offset] + tail[:index] + rules + tail[index:], encoding="utf-8")
    board.BuildConnectivity()
    if not k.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("Could not fill GND zones")
    if not k.SaveBoard(str(args.output), board):
        raise RuntimeError(f"Could not save {args.output}")


if __name__ == "__main__":
    main()
