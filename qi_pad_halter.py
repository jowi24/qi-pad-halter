# Baut den Qi-Pad-Halter parametrisch in FreeCAD.
# Aufruf: /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd qi_pad_halter.py
# Alle Maße stehen danach im Spreadsheet "Params" der .FCStd und können dort geändert werden.
#
# Koordinaten: Ursprung = Pad-Mitte auf dem Schubladenboden, -X = linke Wand, -Y = vordere Wand.

import os
import FreeCAD as App
import Part
import Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
doc = App.newDocument("QiPadHalter")

# ---------- Parameter ----------
params = [
    # alias, wert/formel, beschreibung
    ("padD",       "57.7",   "Durchmesser Qi-Pad"),
    ("padT",       "5.9",    "Dicke Qi-Pad"),
    ("padTop",     "33.5",   "Höhe Pad-Oberseite über Boden"),
    ("gap",      "0.3",  "Spiel Pad <-> Röhre (radial)"),
    ("wall",       "2",    "Wandstärke Röhre"),
    ("ledge",      "3",    "Breite Auflagering innen"),
    ("lipH",       "3",    "Rand über Auflage (seitliche Führung)"),
    ("cableW",     "5",    "Breite Kabelausschnitt"),
    ("cableDepth", "4",    "Kabelausschnitt reicht so tief unter Auflage"),
    ("slotW",      "6",    "Breite Lüftungsschlitze"),
    ("slotBottom", "4",    "Unterkante Lüftungsschlitze"),
    ("distLeft",   "120",  "Pad-Mitte -> linke Schubladenwand"),
    ("distFront",  "130",   "Pad-Mitte -> vordere Schubladenwand"),
    ("barW",       "10",   "Breite Anschlagsteg"),
    ("barH",       "3",    "Höhe Anschlagsteg"),
    ("testBelow",  "3",    "Passtest: so viel unterhalb der Fase mitdrucken"),
    # abgeleitet
    ("rIn",         "=padD / 2 + gap",       "Innenradius oben (Pad-Aufnahme)"),
    ("rOut",         "=rIn + wall",              "Außenradius"),
    ("rHole",         "=rIn - ledge",             "Radius offene Mitte"),
    ("ledgeZ",     "=padTop - padT",          "Höhe Auflagefläche"),
    ("tubeH",          "=ledgeZ + lipH",          "Gesamthöhe Röhre"),
]
sheet = doc.addObject("Spreadsheet::Sheet", "Params")
for i, (alias, value, desc) in enumerate(params, start=1):
    sheet.set(f"A{i}", desc)
    sheet.set(f"B{i}", value if value.startswith("=") else "=" + value)
    sheet.setAlias(f"B{i}", alias)
doc.recompute()


def expr(obj, prop, e):
    obj.setExpression(prop, e)


def cyl(name, r, h, z="0"):
    o = doc.addObject("Part::Cylinder", name)
    expr(o, "Radius", r)
    expr(o, "Height", h)
    expr(o, "Placement.Base.z", z)
    return o


def box(name, l, w, h, x, y, z):
    o = doc.addObject("Part::Box", name)
    for p, e in (("Length", l), ("Width", w), ("Height", h),
                 ("Placement.Base.x", x), ("Placement.Base.y", y), ("Placement.Base.z", z)):
        expr(o, p, e)
    return o


# ---------- Röhre ----------
outer = cyl("Aussen", "Params.rOut", "Params.tubeH")
cuts = [
    # Innenbohrung unten bis kurz unter die Auflage
    cyl("BohrungUnten", "Params.rIn", "Params.ledgeZ - Params.ledge", "-1"),
    # Offene Mitte durch alles
    cyl("Mitte", "Params.rHole", "Params.tubeH + 2", "-1"),
    # Pad-Aufnahme oberhalb der Auflage
    cyl("PadAufnahme", "Params.rIn", "Params.lipH + 1", "Params.ledgeZ"),
    # Kabelausschnitt nach links durch Wand und Auflage
    box("Kabel", "Params.wall + Params.ledge + 2", "Params.cableW", "Params.lipH + Params.cableDepth + 1",
        "-Params.rOut - 1", "-Params.cableW / 2", "Params.ledgeZ - Params.cableDepth"),
]
# 45°-Fase unter der Auflage, damit sie ohne Stützen druckbar ist
cone = doc.addObject("Part::Cone", "Fase")
expr(cone, "Radius1", "Params.rIn")
expr(cone, "Radius2", "Params.rHole")
expr(cone, "Height", "Params.ledge")
expr(cone, "Placement.Base.z", "Params.ledgeZ - Params.ledge - 0.001")
cuts.append(cone)

# Lüftungsschlitze schräg (45/135/225/315°), also weg von Kabel (links) und Anschlägen
for k, a in enumerate((45, 135, 225, 315)):
    s = doc.addObject("Part::Box", f"Schlitz{k}")
    expr(s, "Length", "Params.wall + 2")
    expr(s, "Width", "Params.slotW")
    expr(s, "Height", "Params.ledgeZ - Params.ledge - Params.slotBottom - 2")
    s.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), a)
    expr(s, "Placement.Base.x", f"(Params.rIn - 1) * cos({a} deg) + Params.slotW / 2 * sin({a} deg)")
    expr(s, "Placement.Base.y", f"(Params.rIn - 1) * sin({a} deg) - Params.slotW / 2 * cos({a} deg)")
    expr(s, "Placement.Base.z", "Params.slotBottom")
    cuts.append(s)

tool = doc.addObject("Part::MultiFuse", "Ausschnitte")
tool.Shapes = cuts
tube = doc.addObject("Part::Cut", "Roehre")
tube.Base = outer
tube.Tool = tool

# ---------- Anschlagstege ----------
barLeft = box("StegLinks", "Params.distLeft - Params.rIn - Params.wall / 2", "Params.barW", "Params.barH",
              "-Params.distLeft", "-Params.barW / 2", "0")
barFront = box("StegVorne", "Params.barW", "Params.distFront - Params.rIn - Params.wall / 2", "Params.barH",
               "-Params.barW / 2", "-Params.distFront", "0")

body = doc.addObject("Part::MultiFuse", "QiPadHalter")
body.Shapes = [tube, barLeft, barFront]
body.Refine = True
doc.recompute()

shape = body.Shape
assert shape.isValid(), "Shape ungültig"
bb = shape.BoundBox
print(f"Volumen {shape.Volume / 1000:.1f} cm3, Solids {len(shape.Solids)}")
print(f"BoundBox x {bb.XMin:.1f}..{bb.XMax:.1f}  y {bb.YMin:.1f}..{bb.YMax:.1f}  z {bb.ZMin:.1f}..{bb.ZMax:.1f}")

# ---------- Passtest: nur der obere Ring mit Auflage, Rand und Kabelausschnitt ----------
testCut = box("PasstestBereich", "2 * Params.rOut + 2", "2 * Params.rOut + 2", "Params.tubeH",
              "-Params.rOut - 1", "-Params.rOut - 1", "Params.ledgeZ - Params.ledge - Params.testBelow")
test = doc.addObject("Part::Common", "Passtest")
test.Base = tube
test.Tool = testCut
doc.recompute()
testShape = test.Shape.copy()
testShape.translate(App.Vector(0, 0, -testShape.BoundBox.ZMin))
print(f"Passtest: Hoehe {testShape.BoundBox.ZLength:.1f} mm, Volumen {testShape.Volume / 1000:.1f} cm3")

doc.saveAs(os.path.join(HERE, "qi-pad-halter.FCStd"))
Mesh.export([body], os.path.join(HERE, "qi-pad-halter.stl"))

testMesh = Mesh.Mesh()
testMesh.addFacets(testShape.tessellate(0.05))
testMesh.write(os.path.join(HERE, "qi-pad-halter-passtest.stl"))
