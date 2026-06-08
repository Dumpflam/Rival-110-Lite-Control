MOUSE_SVG_TEMPLATE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 390" width="100" height="390">

  <!-- Cień -->
  <ellipse cx="50" cy="383" rx="38" ry="6" fill="#000" opacity="0.25"/>

  <!-- Główny korpus -->
  <path d="
    M 8 80
    Q 8 20, 50 15
    Q 92 20, 92 80
    L 94 280
    Q 94 370, 50 370
    Q 6 370, 6 280
    Z
  " fill="#1a1a1a" stroke="#3a3a3a" stroke-width="1.5"/>

  <!-- Linia podziału przycisków -->
  <line x1="50" y1="15" x2="50" y2="115" stroke="#2a2a2a" stroke-width="1"/>

  <!-- Lewy przycisk -->
  <path d="M 8 80 Q 8 20 50 15 L 50 115 Q 30 115 15 108 Q 8 100 8 80Z"
    fill="#222222" stroke="#333333" stroke-width="0.5"/>

  <!-- Prawy przycisk -->
  <path d="M 92 80 Q 92 20 50 15 L 50 115 Q 70 115 85 108 Q 92 100 92 80Z"
    fill="#212121" stroke="#333333" stroke-width="0.5"/>

  <!-- Scroll wheel -->
  <rect x="40" y="42" width="20" height="36" rx="10" fill="#2a2a2a" stroke="#444444" stroke-width="0.8"/>
  <rect x="44" y="55" width="12" height="10" rx="3" fill="#383838"/>

  <!-- Boczne przyciski -->
  <rect x="2" y="160" width="6" height="22" rx="3" fill="#252525" stroke="#3a3a3a" stroke-width="0.5"/>
  <rect x="2" y="188" width="6" height="22" rx="3" fill="#252525" stroke="#3a3a3a" stroke-width="0.5"/>

  <!-- Połysk górny -->
  <path d="M 20 50 Q 50 35 80 50" fill="none" stroke="#ffffff" stroke-width="0.8" opacity="0.07"/>

  <!-- Z1 — strefa górna (scroll wheel glow) -->
  <ellipse id="zone_z1" cx="50" cy="95" rx="22" ry="10" fill="{z1}" opacity="0.9"/>
  <ellipse cx="50" cy="95" rx="22" ry="10" fill="none" stroke="{z1}" stroke-width="1" opacity="0.5"/>

  <!-- Z2 — strefa środkowa (logo/grip) -->
  <ellipse id="zone_z2" cx="50" cy="210" rx="26" ry="32" fill="{z2}" opacity="0.85"/>
  <ellipse cx="50" cy="210" rx="26" ry="32" fill="none" stroke="{z2}" stroke-width="1" opacity="0.45"/>

  <!-- Z3 — strefa dolna (base) -->
  <ellipse id="zone_z3" cx="50" cy="320" rx="30" ry="22" fill="{z3}" opacity="0.9"/>
  <ellipse cx="50" cy="320" rx="30" ry="22" fill="none" stroke="{z3}" stroke-width="1" opacity="0.5"/>

</svg>
"""
