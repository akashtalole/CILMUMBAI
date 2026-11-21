# Follow the Rupee: three-minute demo

Open <https://akashtalole.github.io/CILMUMBAI/rupee/> (works on a phone; no login, no server). Offline:
`cd app && hishob rupee build && hishob rupee export --out ../docs/rupee/json` then
`cd web && npm run build:rupee`, copy `dist-rupee/` next to `json/`, and serve the folder.

**The pitch (one tool): open a ward, see where its money went, what is in question, who answers for it, and what
to fix next.**

1. **The money (15 s).** Top cards: ₹13.43 cr spent of ₹14.91 cr; ₹3.07 cr on fixes that failed within 30 days;
   ₹3.22 cr in question.
2. **A ward (45 s).** Wards tab, worst grade first. The map is coloured by grade. Read the first lines of the Claude
   summary; point at the budget bar, the spend by contractor and the four scores ("50 means as expected for these
   jobs, given method, rain and ward").
3. **Audit accuracy (45 s).** Audit flags: 109 over-billed, 45 duplicates, 493 paid during the guarantee. Open a
   duplicate: "billed ₹1,67,957 with no complaint, 3 days after WO25-01977 for the same work". Click the row link: it
   opens that exact line of the dataset. Say: rules in code with stated thresholds, so the same data always gives the
   same flags; normal 20-30% variation is never flagged; "failed fix paid again" is shown as a lead, not counted.
4. **Fair accountability (30 s).** Contractors: Mahalaxmi grade E, Deccan B. Fair because each job is compared with
   the same method and weather; we tested it, and rain did not explain failures, the method did. Volume is not
   punished. DLP payments count against the ward that approved them, not the contractor.
5. **Next rupee (30 s).** Top item: open manhole on the Eastern Express Highway, 228 m from a tide-sensitive flood
   spot, a fatal accident, near Sion Hospital. Method chosen is the one that fails least, not the cheapest; roads
   under DLP go back to the original contractor at ₹0.
6. **Citizen (15 s).** My complaint, switch to मराठी, try BMC25-000047: fixed, failed within 30 days, bill flagged.

**Where Claude is:** it writes every scorecard and ward summary from the computed figures, and code checks each one:
every number must be one of the figures, no accusations, not cut off; otherwise a template is used. Findings never
depend on the model.

Outputs for the judges: `results/flags.csv`, `next_rupee.csv`, `scorecards.csv`, `complaints_linked.csv`.
