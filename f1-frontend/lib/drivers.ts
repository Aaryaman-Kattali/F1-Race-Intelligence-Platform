export type DriverMeta = {
  code: string;
  name: string;
};

// Curated, not exhaustive — drivers confirmed present in the 4 ingested
// circuits' data. Add more as more circuits get backfilled.
export const DRIVERS: DriverMeta[] = [
  { code: "HAM", name: "Lewis Hamilton" },
  { code: "VER", name: "Max Verstappen" },
  { code: "NOR", name: "Lando Norris" },
  { code: "PIA", name: "Oscar Piastri" },
  { code: "LEC", name: "Charles Leclerc" },
  { code: "SAI", name: "Carlos Sainz" },
  { code: "RUS", name: "George Russell" },
  { code: "PER", name: "Sergio Perez" },
  { code: "ALO", name: "Fernando Alonso" },
  { code: "GAS", name: "Pierre Gasly" },
];
