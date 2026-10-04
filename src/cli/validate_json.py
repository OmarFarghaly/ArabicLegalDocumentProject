import json
from collections import Counter

json_path = "data/processed/articles.json"

with open(json_path, "r", encoding="utf-8") as file:
    records = json.load(file)

null_counts = Counter()
empty_counts = Counter()

for index, record in enumerate(records):
    for field, value in record.items():

        if value is None:
            null_counts[field] += 1

        elif isinstance(value, str) and not value.strip():
            empty_counts[field] += 1

print(f"Total records: {len(records)}")
print()

print("Problems by attribute:")
print("-" * 60)

all_fields = set(null_counts) | set(empty_counts)

for field in sorted(all_fields):
    null_count = null_counts.get(field, 0)
    empty_count = empty_counts.get(field, 0)
    total = null_count + empty_count

    print(
        f"{field:<20} "
        f"total: {total:<5} "
        f"NULL: {null_count:<5} "
        f"EMPTY: {empty_count}"
    )