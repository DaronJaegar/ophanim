"""Attack-path graph, Risk score and the 'one fix'  (Aaron, Module B).

Risk = sum over every simple path (attacker -> crown jewel, up to 4 hops) of
       (product of edge 'ease' values on the path) x (value of the jewel).
A path is 'open' if its product of eases is >= OPEN_THRESHOLD.
"""
import math
import networkx as nx

OPEN_THRESHOLD = 0.1
JEWELS = {"money": 10, "records": 10}

# Each edge's ease = product of its factors. A fix changes one factor.
# verified=True: seen by an API / the agent.  False: reported in the onboarding chat.
DEMO_EDGES = [
    ("attacker", "gmail",    {"breached_password": 0.8, "no_2sv": 0.7}, True),
    ("gmail",    "bank",     {"resets_login": 0.9}, False),
    ("bank",     "money",    {"transfer": 0.8}, False),
    ("gmail",    "invoices", {"reads_mail": 0.9}, True),
    ("invoices", "money",    {"vendor_redirect": 0.6}, False),
    ("attacker", "drive",    {"public_link_unknown": 0.3}, True),   # 1.0 once a live share is seen
    ("drive",    "records",  {"contains": 1.0}, True),
    ("attacker", "pc",       {"phishing_attachment": 0.3}, False),
    ("pc",       "records",  {"can_reach_files": 0.8}, True),
]
LABELS = {"attacker": "Attacker", "gmail": "Priya's Gmail", "bank": "Bank login",
          "invoices": "Invoice emails", "money": "Clinic money", "drive": "Records folder",
          "records": "Patient records", "pc": "Front-desk PC"}

# Fixes the owner can apply, and what each one changes.
FIXES = {
    "enable_2sv":   {"edge": ("attacker", "gmail"), "factor": "no_2sv", "value": 0.1,
                     "text": "Turn on 2-step login for Priya"},
    "make_private": {"edge": ("attacker", "drive"), "factor": "public_link_unknown", "value": 0.0,
                     "text": "Make the records folder private"},
    "patch_pc":     {"edge": ("attacker", "pc"), "factor": "phishing_attachment", "value": 0.1,
                     "text": "Update the front-desk PC and its antivirus"},
}

def build_demo_graph():
    g = nx.DiGraph()
    for a, b, factors, verified in DEMO_EDGES:
        g.add_edge(a, b, factors=dict(factors), verified=verified, live=False)
    return g

def ease(g, a, b):
    return math.prod(g[a][b]["factors"].values())

def paths(g):
    """Every attacker -> jewel path with its ease and risk, worst first."""
    out = []
    for jewel, value in JEWELS.items():
        if jewel not in g:
            continue
        for p in nx.all_simple_paths(g, "attacker", jewel, cutoff=4):
            e = math.prod(ease(g, a, b) for a, b in zip(p, p[1:]))
            out.append({"path": p, "ease": round(e, 3), "risk": round(e * value, 2),
                        "open": e >= OPEN_THRESHOLD})
    return sorted(out, key=lambda x: -x["risk"])

def total_risk(g):
    return round(sum(p["risk"] for p in paths(g)), 2)

def apply_fix(g, fix_name):
    f = FIXES[fix_name]
    a, b = f["edge"]
    d = g[a][b]
    target = d["orig"] if d.get("live") else d["factors"]   # if the edge is under live attack, fix the saved values
    target[f["factor"]] = f["value"]

def set_factor(g, a, b, factor, value):
    """A measured fact (e.g. the PC's update age) sets one factor. Under a live attack the saved values change."""
    d = g[a][b]
    (d["orig"] if d.get("live") else d["factors"])[factor] = value

def one_fix(g):
    """Greedy: try each fix on a copy, keep the one that removes the most risk."""
    base = total_risk(g)
    best = None
    for name in FIXES:
        trial = g.copy()
        for u, v in trial.edges:               # deep-copy the factor dicts
            trial[u][v]["factors"] = dict(g[u][v]["factors"])
            if "orig" in g[u][v]:
                trial[u][v]["orig"] = dict(g[u][v]["orig"])
        apply_fix(trial, name)
        drop = base - total_risk(trial)
        closed = sum(p["open"] for p in paths(g)) - sum(p["open"] for p in paths(trial))
        if best is None or drop > best["risk_drop"]:
            best = {"fix": name, "text": FIXES[name]["text"], "risk_drop": round(drop, 2),
                    "paths_closed": closed}
    return best

def mark_live(g, a, b, factor="live_attack"):
    """A live attacker signal makes that edge certain (ease 1.0) and red on the console.
    The normal values are saved so they come back once the attack is cleaned up."""
    if not g.has_edge(a, b):
        g.add_edge(a, b, factors={}, verified=True, live=False)
    d = g[a][b]
    if not d["live"]:
        d["orig"] = dict(d["factors"])
    d["factors"] = {factor: 1.0}
    d["live"] = True

def clear_live(g, a, b):
    if g.has_edge(a, b) and g[a][b]["live"]:
        d = g[a][b]
        d["factors"] = d.pop("orig", d["factors"])
        d["live"] = False

def path_sentence(p):
    names = [LABELS.get(n, n) for n in p["path"]]
    return " → ".join(names)

def to_json(g):
    """For the console (Cytoscape)."""
    nodes = [{"data": {"id": n, "label": LABELS.get(n, n),
                       "kind": "jewel" if n in JEWELS else ("attacker" if n == "attacker" else "asset")}}
             for n in g.nodes]
    edges = [{"data": {"id": f"{a}-{b}", "source": a, "target": b, "ease": round(ease(g, a, b), 2),
                       "factors": dict(d["factors"]), "verified": d["verified"], "live": d["live"]}}
             for a, b, d in g.edges(data=True)]
    return {"nodes": nodes, "edges": edges, "risk": total_risk(g),
            "open_paths": sum(p["open"] for p in paths(g)), "one_fix": one_fix(g)}
