# Fulfillment and customer counting logic

This file summarizes how the rewritten visit-tracking code measures customer fulfillment and splits allocated vs. overflow traffic.

## Recording visits with needs

* When a regular customer enters a store, the visit is tagged as `allocated` for their assigned shop or `overflow` for any subsequent shop. The basket size on entry is recorded to anchor fulfillment math.【F:economy_sim.py†L2717-L2722】【F:economy_sim.py†L2796-L2807】
* A visit is only recorded if at least one item was bought there. Recorded visits capture the store, visit type, items purchased, and the fulfillment percentage `(items_purchased_at_store / basket_on_entry) * 100`.【F:economy_sim.py†L2796-L2807】
* After shopping, each recorded visit feeds two trackers per store: the fulfillment percentage list (`daily_fulfillment_data`) and the visit counters split by `allocated` vs. `overflow`. These numbers later drive the averages printed in the summary.【F:economy_sim.py†L2847-L2855】
* Reputation also updates per visit: -1 for ≤30% fulfillment, +1 for ≥80%, and an extra +1 when the only store hits ~100%.【F:economy_sim.py†L2856-L2863】

## Handling zero-need or external visit payloads

* Utility helpers `record_store_visit_metrics` and `record_single_store_visit` process arbitrary visit payloads (e.g., tests or external callers). They default unknown visit types to `allocated`, ignore visits missing store bookkeeping, and short-circuit zero-need visits while optionally tallying them in `routed_no_need_counts`.【F:economy_sim.py†L2402-L2459】
* When a visit carries needs, the helper computes fulfillment, appends it to the appropriate allocated/overflow list, increments the matching counter, marks the visit as recorded, and applies the same reputation rules as above.【F:economy_sim.py†L2451-L2474】

## Customer summary vs. fulfillment denominator

* Customer counts in the daily summary come from unique stores where the shopper actually made a purchase, keyed by visit type. A single customer can increment both `allocated` and `overflow` counts if they buy at multiple stores.【F:economy_sim.py†L2865-L2871】
* Fulfillment averages only consider recorded visits (i.e., where needs > 0 and at least one item was purchased). The summary totals use the length of the allocated/overflow fulfillment lists, so customers who bought nothing—or who arrived with no needs and were ignored by the helpers—do not affect the fulfillment denominator.【F:economy_sim.py†L2477-L2487】【F:economy_sim.py†L2796-L2807】
