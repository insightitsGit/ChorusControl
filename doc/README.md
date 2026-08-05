# ChorusControl design docs

| Doc | Purpose |
|-----|---------|
| **[ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md)** | Full design **v1.8.1** — §3.7.4a Client AI chats · §11.6 Assistant literacy + full execute matrix · Logs |
| **[Ops-Assistant-Actions.md](./Ops-Assistant-Actions.md)** | **Per-tab prompt → `execute.type` agent KB** (code: `assistant_actions.py`) |
| **[Ops-Assistant.md](./Ops-Assistant.md)** | Dashboard literacy + how gated execute works |
| **[Client-Chats.md](./Client-Chats.md)** | End-user chat history + PrismCortex compact requirements |
| **[ChorusControl-Implementation-Plan.md](./ChorusControl-Implementation-Plan.md)** | Build checklist — no phases |
| **[ChorusControl-Review-Resolutions.md](./ChorusControl-Review-Resolutions.md)** | R01–R08 / I01–I05 locked |
| [ChorusControl-Design-Overview.md](./ChorusControl-Design-Overview.md) | Short product overview |
| [ChorusControl-Design-Gaps-and-Solutions.md](./ChorusControl-Design-Gaps-and-Solutions.md) | Normative architecture (mirrors COMPLETE) |
| [ChorusControl-Design-Review.md](./ChorusControl-Design-Review.md) | Independent review (historical v1.7; see COMPLETE for v1.8+) |
| [ChorusControl-Implementer-Handoff.md](./ChorusControl-Implementer-Handoff.md) | WP1–WP12 + post-WP addenda (Logs, Client chats, action catalog) |
| [ChorusControl-Implementation-Gap-Report.md](./ChorusControl-Implementation-Gap-Report.md) | Design vs code scorecard |
| [ai-overview.md](./ai-overview.md) | Short agent/Cursor overview |
| [Healthcare-Demo.md](./Healthcare-Demo.md) | Aurora Health demo walkthrough |
| [PACKAGING.md](./PACKAGING.md) | Wheels / extras / containers |
| [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md) | Website handoff (**other agent**) |
| **[benchmarks/prism-pack/](./benchmarks/prism-pack/)** | **Pack family Race E** — research note + COMPARISON_REPORT (Pack lanes; CC hosts/governs) |

**Product:** ChorusControl — AI Operations Platform (mother `[server]` + fleet `[agent]`).

### Shipped design slices (v1.8.x)

| Slice | Design | Doc |
|-------|--------|-----|
| Ops Logs bus | `/logs` · fleet logs-batch | COMPLETE / README |
| Client AI chats | §3.7.4a | [Client-Chats.md](./Client-Chats.md) |
| Ops Assistant literacy | §11.6 teach | [Ops-Assistant.md](./Ops-Assistant.md) |
| Ops Assistant execute catalog | §11.6 + 1.8.1 | [Ops-Assistant-Actions.md](./Ops-Assistant-Actions.md) |
