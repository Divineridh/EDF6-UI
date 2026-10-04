import sys
from sgo import Sgo

sys.stdout.reconfigure(encoding="utf-8")

def props(p):
    out = []
    for it in p:
        if isinstance(it, list) and it and isinstance(it[0], str):
            out.append("%s=%s" % (it[0], it[1] if len(it) > 1 else ""))
    return " ".join(out)

def print_tree(node, depth=0):
    i = 0
    while i < len(node):
        name = node[i][0]
        children = node[i + 1] if i + 1 < len(node) else 0
        print("%s%s" % ("    " * depth, name))
        if isinstance(children, list):
            print_tree(children, depth + 1)
        i += 2

sgo = Sgo(open(sys.argv[1], "rb").read())
tree = sgo.tree()
names = sgo.names()
print("root nodes:", len(tree))
for i, n in enumerate(tree):
    name = names.get(i, "?")
    if not isinstance(n, list) or not n:
        print("%2d %-26s %s" % (i, name, n)); continue
    if isinstance(n[0], str):
        cls = n[0]
        skin = n[1] if len(n) > 1 and isinstance(n[1], str) else ""
        pos = n[2] if len(n) > 2 else ""
        area = n[3] if len(n) > 3 else ""
        flags = n[4] if len(n) > 4 else ""
        coord = "%s,%s" % (n[5], n[6]) if len(n) > 6 else ""
        extra = props(n[7]) if len(n) > 7 and isinstance(n[7], list) else ""
        print("%2d %-26s %-10s pos=%-22s area=%-26s flags=%-16s hv=%-4s %-30s %s" % (
            i, name, cls, pos, area, flags, coord, skin.replace("app:/UI/", ""), extra[:80]))
    elif isinstance(n[0], list) and len(n[0]) > 1 and isinstance(n[0][1], str):
        print("%2d %-26s REF %-21s %s" % (i, name, n[0][1], props(n[1])[:120] if len(n) > 1 else ""))
    else:
        print("%2d %-26s %s" % (i, name, str(n)[:120]))

for i, n in enumerate(tree):
    if names.get(i) == "layout_tree":
        print("\nlayout_tree:")
        print_tree(n)
