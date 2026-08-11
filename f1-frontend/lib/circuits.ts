export type Circuit = {
  slug: string;
  name: string; // must match backend's canonical circuit_name exactly
  country: string;
  viewBox: string;
  path: string; // stylized schematic outline, not GPS-accurate
};

export const CIRCUITS: Circuit[] = [
  {
    slug: "hungarian",
    name: "Hungarian Grand Prix",
    country: "Hungary",
    viewBox: "0 0 400 280",
    path: "M 80 200 C 60 180 60 140 90 120 C 110 108 100 80 130 70 C 160 60 190 70 200 90 C 210 108 240 100 260 115 C 285 132 290 160 270 178 C 250 196 255 215 230 222 C 200 230 170 220 150 225 C 120 232 100 220 80 200 Z",
  },
  {
    slug: "italian",
    name: "Italian Grand Prix",
    country: "Italy",
    viewBox: "0 0 400 280",
    path: "M 40 140 L 320 140 C 340 140 350 130 350 115 C 350 100 335 92 320 96 L 300 102 C 285 106 275 98 278 85 C 281 72 295 68 310 72 L 340 80 C 355 84 365 75 362 60 L 40 60 C 25 60 15 72 20 88 C 25 104 40 108 55 104 L 75 98 C 90 94 100 105 96 118 C 92 131 78 135 63 130 L 40 122 C 25 117 15 128 20 140 Z",
  },
  {
    slug: "belgian",
    name: "Belgian Grand Prix",
    country: "Belgium",
    viewBox: "0 0 400 280",
    path: "M 60 230 C 50 200 70 190 85 175 C 100 160 90 140 110 125 C 128 111 122 90 145 82 C 168 74 195 85 200 105 C 205 122 230 118 250 128 C 275 140 300 130 320 105 C 335 86 360 85 370 105 C 380 125 365 145 345 150 C 320 156 315 180 295 190 C 270 202 250 190 225 195 C 195 201 175 220 145 222 C 115 224 90 235 60 230 Z",
  },
  {
    slug: "british",
    name: "British Grand Prix",
    country: "United Kingdom",
    viewBox: "0 0 400 280",
    path: "M 100 220 C 75 210 65 185 80 165 C 95 145 80 120 100 105 C 118 91 115 65 145 60 C 175 55 195 75 190 100 C 186 120 210 125 230 115 C 255 103 285 110 295 135 C 305 160 330 155 345 175 C 358 192 350 215 325 220 C 300 225 290 210 270 212 C 245 215 230 235 200 232 C 170 229 155 210 130 215 C 118 217 110 220 100 220 Z",
  },
];
