"""One-time diagnostic/migration script. Not part of the regular pipeline."""

"""Probe FastF1 session.results and session.laps columns for Qualifying and Race."""
import fastf1
import warnings
warnings.filterwarnings('ignore')

fastf1.Cache.enable_cache('data/fastf1_cache')

# Load a qualifying session
print("=== QUALIFYING SESSION (Hungary 2024) ===")
q_session = fastf1.get_session(2024, 'Hungary', 'Qualifying')
q_session.load()

print("\nResults columns:", list(q_session.results.columns))
print("\nFirst result row:")
first = q_session.results.iloc[0]
for col in q_session.results.columns:
    print(f"  {col}: {first[col]} (type: {type(first[col]).__name__})")

print("\n\nLaps columns:", list(q_session.laps.columns))
print(f"Laps shape: {q_session.laps.shape}")
if not q_session.laps.empty:
    first_lap = q_session.laps.iloc[0]
    for col in q_session.laps.columns:
        print(f"  {col}: {first_lap[col]} (type: {type(first_lap[col]).__name__})")

# Also check Race laps for compound/stint/tyre_life
print("\n\n=== RACE SESSION LAPS (Hungary 2024) ===")
r_session = fastf1.get_session(2024, 'Hungary', 'Race')
r_session.load()

print("Race laps columns:", list(r_session.laps.columns))
print(f"Race laps shape: {r_session.laps.shape}")
if not r_session.laps.empty:
    first_lap = r_session.laps.iloc[5]  # skip first few which might be formation
    for col in r_session.laps.columns:
        print(f"  {col}: {first_lap[col]} (type: {type(first_lap[col]).__name__})")
