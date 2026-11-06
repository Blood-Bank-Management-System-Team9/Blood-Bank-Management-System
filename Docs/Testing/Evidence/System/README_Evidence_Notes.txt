BBMS SYSTEM VALIDATION - SELECTED SCREENSHOT EVIDENCE

Place the contents of Evidence/System into your project folder:
Docs/Testing/Evidence/System/

The screenshots are selected from the uploaded collection and renamed by workflow.
They are evidence of the visible screen state only; do not automatically mark a test PASS.

Important limitations / additional tests still needed:
- Donor registration form and validation screenshots do not show a successful registration confirmation.
- Record Donation screenshot shows the entry form; verify successful submission and resulting inventory separately.
- The inventory screenshots show different test states. Explain the data state and sequence in the report; do not treat differing counts as contradictory without checking the underlying test setup.
- Request screenshots demonstrate pending review, request details, and rejection. They do not demonstrate approval, blood issue, or stock deduction.
- The login screenshot demonstrates the login page; invalid-login screenshot demonstrates a rejected login attempt.
- 403/404 pages and server logs were not included as successful evidence. If documenting access-control defects, retain them separately and report the context.
