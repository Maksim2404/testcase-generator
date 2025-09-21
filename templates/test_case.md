---
id: APP1-TC-001
app: APP1
area: Billing > Invoices
suite: Regression            # Smoke | Regression | E2E
type: Functional             # Functional | UX | Perf | Security | E2E
priority: P3                 # P0..P3
status: Ready                # Draft | Ready | Deprecated
story_refs:
  - group/app1#123           # cross-project GitLab issue links
bug_refs: []
owner: "@maksim"                # your GitLab username
automation:
  status: NotAutomated       # NotAutomated | Planned | Automated
  mapping: ""
links: []                    # figma:// swagger:// etc.
---

# Title
Invoice: create + mandatory fields + success toast

## Preconditions
- Seed customer C123 exists.
- User has BillingEditor role.

## Steps & Expected
1. Open **Invoices** → click **New**  
   **Expected:** New Invoice form appears.
2. Fill mandatory fields (Customer=C123, Amount=100, Date=today)  
   **Expected:** Save enabled; validation passes.
3. Click **Save**  
   **Expected:** Success toast; invoice listed with status **Draft**.

## Negative / Edge
- Amount = 0 → validation error; Save disabled.

## Test Data
| Field  | Value |
|--------|-------|
| Amount | 100   |

## Notes
Screenshots: `/testcase-generator/apps/APP1/areas/billing/_customer/APP1-TC-001/`