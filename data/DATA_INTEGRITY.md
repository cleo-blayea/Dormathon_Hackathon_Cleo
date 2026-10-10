# GenBuddy Data Integrity Record

> These SHA-256 hashes were recorded after the data corrections (duplicate
> removal, maintenance chronology fix, power recalculation) were applied.
> Use them to verify that the original datasets have not been modified.

## Corrected Dataset Hashes (SHA-256)

| File | SHA-256 | Records |
|------|---------|---------|
| generator_data.csv | 937759e9c6b2db3ee62b4968403b740b5709736e0f5b2c8276146f611c418838 | 176 |
| ats_events.csv | 2a337ca65f8a638965455d4a45616304fcd7dde9175c0e0545edfc5457819c79 | 176 |
| maintenance_history.csv | 18398fc1ebf2439a77df648e147563d652bdbe87570eb473b6b5929ea6991fc0 | 4 |

## Verification

To verify data integrity, run:

```bash
python -c "import hashlib; print(hashlib.sha256(open('data/generator_data.csv','rb').read()).hexdigest())"
```

Compare the output to the hashes above.

## Protection

- `scripts/generate_data.py` refuses to overwrite existing data files
  without the `--force` flag.
- `data/backup/` contains pre-correction copies of the original CSVs.
