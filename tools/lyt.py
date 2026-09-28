import sys
from sgo import Sgo

sys.stdout.reconfigure(encoding="utf-8")

def props(p):
    out = []
    for it in p:
        if isinstance(it, list) and it and isinstance(it[0], str):
            out.append("%s=%s" % (it[0], it[1] if len(it) > 1 else ""))
    return " ".join(out)

data = open(sys.argv[1], "rb").read()
tree = Sgo(data).tree()
print("root nodes:", len(tree))
for i, n in enumerate(tree):
    if not isinstance(n, list) or not n:
        print(i, n); continue
    if isinstance(n[0], str):
        cls = n[0]
        skin = n[1] if len(n) > 1 and isinstance(n[1], str) else ""
        pos = n[2] if len(n) > 2 else ""
        area = n[3] if len(n) > 3 else ""
        extra = props(n[7]) if len(n) > 7 and isinstance(n[7], list) else ""
        print("%2d %-12s pos=%-24s area=%-26s %-42s %s" % (i, cls, pos, area, skin.replace("app:/UI/", ""), extra[:90]))
    elif isinstance(n[0], list):
        name = n[0][1] if len(n[0]) > 1 else "?"
        print("%2d NAMED %-28s %s" % (i, name, props(n[1])[:120] if len(n) > 1 else ""))
