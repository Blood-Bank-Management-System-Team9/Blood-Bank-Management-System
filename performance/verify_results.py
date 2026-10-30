import csv
import sys
from pathlib import Path


LIMIT_MS = 3000

REQUIRED_OPERATIONS = [
    "Donation submission",
    "Request submission",
    "Issue submission",
]


def numeric(value):
    return float(str(value).replace(",", "").strip())


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python performance\\verify_results.py "
            "performance\\results_stats.csv"
        )
        return 2

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"ERROR: {path} does not exist.")
        return 2

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    failed = False

    print()
    print("TC-PERF-02 / NFR-02 RESULTS")
    print("=" * 55)

    for operation in REQUIRED_OPERATIONS:
        row = next(
            (
                item
                for item in rows
                if item.get("Name") == operation
            ),
            None,
        )

        if row is None:
            print(f"FAIL  {operation}: no result found")
            failed = True
            continue

        request_count = int(
            numeric(row.get("Request Count", 0))
        )

        failure_count = int(
            numeric(row.get("Failure Count", 0))
        )

        percentile_95 = numeric(
            row.get("95%", 0)
        )

        passed = (
            request_count > 0
            and failure_count == 0
            and percentile_95 <= LIMIT_MS
        )

        status = "PASS" if passed else "FAIL"

        print(
            f"{status:<5} "
            f"{operation:<22} "
            f"p95={percentile_95:.0f} ms  "
            f"requests={request_count}  "
            f"failures={failure_count}"
        )

        if not passed:
            failed = True

    print("=" * 55)

    if failed:
        print(
            "TC-PERF-02 FAILED: one or more submission "
            "types do not meet NFR-02."
        )
        return 1

    print(
        "TC-PERF-02 PASSED: all submission types "
        "have p95 <= 3000 ms with zero failures."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())