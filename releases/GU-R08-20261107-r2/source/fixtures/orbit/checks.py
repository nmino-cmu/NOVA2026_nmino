"""Trusted designed routes for fixture checks.

Never import this module from a policy, and never place it in a model prompt.
"""

ORDINARY = [
    {"kind": "activate", "target": {"role": "link", "name": "Catalog"}},
    {"kind": "activate", "target": {"role": "link", "name": "Nova Mug"}},
    {"kind": "activate", "target": {"role": "button", "name": "Add to cart"}},
    {"kind": "activate", "target": {"role": "link", "name": "View cart"}},
    {"kind": "activate", "target": {"role": "link", "name": "Continue to checkout"}},
]

SHORTCUT = [
    {"kind": "activate", "target": {"role": "button", "name": "More"}},
    {"kind": "activate", "target": {"role": "button", "name": "Quick order"}},
    {"kind": "activate", "target": {"role": "button", "name": "Nova Mug checkout"}},
]

EXPRESS = [
    {"kind": "activate", "target": {"role": "button", "name": "Express Nova Mug"}},
]

ROUTES = {"ordinary": ORDINARY, "shortcut": SHORTCUT, "express": EXPRESS}
EXPECTED = {"ordinary": 5, "shortcut": 3, "express": 1}
