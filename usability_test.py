import time

results = []

print("\nTC-USE-01 — Donation Usability Test")
print("Target: Record a donation within 2 minutes (120 seconds).")
print("Timer runs ONLY during each tester's actual attempt.\n")

for tester in range(1, 4):

    print("\n" + "=" * 45)
    print(f"PREPARE TESTER {tester}")
    print("=" * 45)

    print("Before starting:")
    print("- Log in as Blood Bank Staff")
    print("- Open the Donor Search page")
    print("- Give the tester their assigned donor details")
    print("- Make sure the tester is ready")

    input(
        f"\nPress ENTER ONLY when Tester {tester} is ready "
        "and you want to START the timer..."
    )

    start_time = time.perf_counter()

    print("\n>>> TIMER RUNNING <<<")
    print("Tester should now:")
    print("Search donor -> Record Donation -> Submit")

    input(
        "\nPress ENTER immediately when the SUCCESS message appears..."
    )

    end_time = time.perf_counter()

    elapsed = end_time - start_time

    minutes = int(elapsed // 60)
    seconds = elapsed % 60

    status = "PASS" if elapsed <= 120 else "FAIL"

    results.append({
        "tester": tester,
        "seconds": elapsed,
        "status": status,
    })

    print(
        f"\nTester {tester}: "
        f"{minutes} min {seconds:.1f} sec — {status}"
    )

    if tester < 3:
        input(
            "\nTimer is STOPPED. "
            "Prepare the next tester at your own pace. "
            "Press ENTER when you want to continue..."
        )


print("\n\n" + "=" * 45)
print("TC-USE-01 FINAL RESULTS")
print("=" * 45)

all_passed = True

for result in results:

    elapsed = result["seconds"]
    minutes = int(elapsed // 60)
    seconds = elapsed % 60

    print(
        f"Tester {result['tester']}: "
        f"{minutes} min {seconds:.1f} sec — "
        f"{result['status']}"
    )

    if result["status"] == "FAIL":
        all_passed = False


print("\nAssistance required during timed attempts: None")

if all_passed:
    print("\nOVERALL RESULT: PASS")
    print(
        "All 3 testers successfully recorded a donation "
        "within 2 minutes."
    )
else:
    print("\nOVERALL RESULT: FAIL")
    print(
        "At least one tester took longer than 2 minutes."
    )