# Ghost Users visual sheet

Local design fallback. Tokens: canvas `#0B1020`, panel `#141C2F`, raised `#1C2740`, text `#F4F7FB`, secondary `#B5C2D8`, border `#2B3853`, accent `#65D9F5`. Verified `#5EE0A0`, deferred `#E6B450`, failed `#FF8A7A`. Inter, 15–16 px body, 12 px radius, 8 px spacing, controls at least 40 px tall. Focus-visible outline. Reduced motion removes transitions.

Desktop 1440×900: navigation 200 px, top strip, summary row (Best verified result, Verification, Usage, Stop reason), graph, inspector 340 px. At 1024 px collapse the navigation and use an inspector drawer. At 768 px show the witness list instead of the graph.

Screens: four-step setup (Target, Goal and starting conditions, Allowed actions and budget, Review and launch), workspace, witness and evidence, run library, read-only playback. Playback shows the ribbon `Recorded investigation`. Empty, loading, and error states use the same shell. No sample metrics.
