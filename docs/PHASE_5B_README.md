# Phase 5B — Successor Transition & Markdown Planning

Phase 5A lifecycle candidates are converted into actions.

Because the supplied dataset has no on-hand inventory, planning inventory is a proxy:
**ceil(chain recent 6-week average × 2 weeks cover)**.

Markdown policy:
- EOL + active successor: 25%
- EOL without active successor: 20%
- WATCH: 10%
- ACTIVE: 0%

Results:
- EOL recommendations: 9
- WATCH: 14
- Successor-active transitions: 18
- Clearance planning units: 22
- Value before markdown: ₹809,700.00
- Value after markdown: ₹693,485.00
- Markdown impact: ₹116,215.00

Validation:
                       check  passed
     60 products represented    True
         no duplicate models    True
  markdown between 0 and 25%    True
 clearance price <= original    True
    clearance price positive    True
clearance units non-negative    True
         successor IDs valid   False

Actual inventory, supplier lead time, contractual EOL dates, and realized markdown sell-through are not present, so these are planning recommendations.
