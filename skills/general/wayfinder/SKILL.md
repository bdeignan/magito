---
name: wayfinder
description: Plan a chunk of work too big for one agent session as a shared map of decision tickets on your issue tracker, then resolve them one at a time until the way to the destination is clear. Charts a map ticket with child tickets, a fog-of-war section for what can't be specified yet, and a frontier of open unblocked tickets worked one per session. Reach for it only when the effort exceeds a single session; for a plan that fits one sitting, use grilling.
disable-model-invocation: true
---

# Wayfinder

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its **decision tickets** — questions whose resolution is a decision, not slices of a build to execute — one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every ticket. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Preflight: does this tracker support wayfinding?

Before charting, confirm `docs/agents/issue-tracker.md` exists and has a **`## Wayfinding operations`** section. That section is where this repo says how the map, its child tickets, claiming, and the frontier query physically work — the skill names those operations and reads that file to perform them. If the file is missing, run `/setup-magito`. If the file exists but has no wayfinding section, this tracker does not support wayfinding — stop and say so, rather than guessing at map plumbing. This check is cheap and it fails clearly, which beats discovering mid-chart that there is nowhere to put the map.

## Plan, don't do

Wayfinder is **planning** by default: each ticket resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off to `/implement`. An effort can override this in its **Notes** — carrying execution into the map itself — but absent that, produce decisions, not deliverables.

## Refer by name

Every map and ticket has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride _inside_ the name, never stand in for it.

## Working with grilling

The default ticket is a **grilling** — a live, one-question-at-a-time interview. In magito `grilling` is user-invoked (`disable-model-invocation: true`), so wayfinder **never invokes it**. Wherever a grilling is called for — naming the destination, mapping the frontier, resolving a grilling ticket — wayfinder **hands off**: it presents what needs deciding and asks the user to run `/grilling`, then continues once they return with the answer. `domain-modeling` stays model-invocable, so wayfinder may invoke that directly. A grilling ticket is human-in-the-loop by definition; the human was always going to be present, so the handoff costs one step, not a workflow.

## The map

The map is a single ticket on this repo's tracker, marked as the map per the Wayfinding-operations section (on GitHub, the `wayfinder:map` label) — the canonical artifact. Its tickets are its child tickets.

The map is an **index**, not a store. It lists the decisions made and points at the tickets that hold their detail; a decision lives in exactly one place — its ticket — so the map never restates it, only gists it and links.

### The map body

The whole map at low resolution, loaded once per session. Open tickets are **not** listed — they are open child tickets, found by the frontier query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is
finding its way to. One or two lines; every session orients to it before choosing a ticket.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Recon

<what the code already does in the area this effort touches — the reconnaissance brief from
charting (see Recon). Lives here, on the map, so every session inherits it and it dies with
the map. One paragraph; link files rather than pasting them.>

## Decisions so far

<!-- the index — one line per closed ticket, each line hard-capped and never wrapped: a gist
     plus the link, nothing longer. The detail lives in the ticket, and "zoom as needed" (see
     Work through the map) fetches anything the line can't hold, so a line never needs to grow.
     Cap the LINE, not the section total — do not rewrite old lines to make the section fit,
     which reintroduces the maintained-document rot #121 rejects. If the whole section
     outgrows a cheap once-per-session read, the map is too big and should be split — a scoping
     signal, not a formatting problem. -->

- [<closed ticket title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Tickets

Each ticket is a **child** of the map; the tracker's id is its identity. Its body is the question, sized to one ~100K-token agent session:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries a `wayfinder:<type>` mark — one of `research`, `prototype`, `grilling`, `task` (see [Ticket types](#ticket-types)).

A session **claims** a ticket before any work, per the Wayfinding-operations *claim* step, so concurrent sessions skip it. An open, unclaimed ticket is takeable. Blocking uses the tracker's native dependency relationship (*Blocking edges*), so the frontier renders in the tracker UI and the human sees what's takeable without opening the map. A ticket is **unblocked** when every ticket blocking it is closed; the **frontier** is the open, unblocked, unclaimed children — the edge of the known.

The answer isn't part of the body — it's recorded on resolution. Assets made while resolving a ticket are linked from it, not pasted in.

**The claim race is real and only narrowed, not closed.** Claiming reads the frontier, then marks a ticket taken — two sessions can both see it unclaimed and both take it. Unlike the journal filename race (#119), randomness can't fix this: the ticket's identity is fixed by the tracker, and no tracker offers atomic test-and-set on a claim. So treat it as a known limit: claim, then immediately re-read the owner and **yield if another session won**. That narrows the window; it does not remove it. The honesty matters more than the narrowing — don't write the skill as if the claim were safe.

## Ticket types

Every ticket is either **HITL** — human in the loop, worked _with_ a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it.

magito has no `/research` or `/prototype` skill, so for those two the type names an **activity**, not a skill to invoke — do the work directly.

- **Research** (AFK): gather a fact a decision waits on — read documentation, a third-party API, or local resources. The agent does this itself, or delegates it to a worker (`~/.magito/workers.toml`, the same roster `/implement` uses) when it wants to spend a prepaid seat instead of the session. Capture findings on a throwaway `research/<name>` branch and link them from the ticket. Use when the knowledge lives outside the current working directory.
- **Prototype** (HITL): raise the fidelity of the discussion with a cheap, rough, concrete artifact to react to — an outline, a stub, a rough take, or throwaway UI/logic code — made by hand. Link the artifact from the ticket. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): conversation, the default case. Hand off — present the ticket and ask the user to run `/grilling` (see [Working with grilling](#working-with-grilling)); invoke `/domain-modeling` directly as needed.
- **Task** (HITL or AFK): manual work that must happen before a _decision_ can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that _does_ rather than decides, and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when done; the answer records what was done and any facts later tickets depend on.

## Recon

Wayfinding drifts in two different ways, and they need two different guards. The map's **Decisions so far** stops the effort drifting *from itself* — session five doesn't re-decide what session two settled. It has no way to read code, so on its own it would not catch drift from code that predates the effort. That is what **recon** guards, inherited from `grilling` (#121): read what the area already does before naming a destination or resolving a decision, so the plan builds on the real codebase instead of re-solving it.

- **Charting runs recon first**, before naming the destination, and writes the brief into the map's `## Recon` section so every later session inherits it.
- **Every HITL ticket runs recon** as part of resolving it — grilling tickets get it for free once the user runs `/grilling` (which opens with its own recon pass); for a prototype or task ticket, do the recon pass yourself before acting.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live tickets lies the **fog of war** — the dim view of decisions you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a ticket clears the fog ahead of it, graduating whatever's now specifiable into fresh tickets — one at a time, until the way to the destination is clear and no tickets remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. Everything here is in scope, just not sharp enough to ticket.

**Fog or ticket?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Ticket when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into ticket-sized pieces.

**Not yet specified** excludes what's already decided, what's already a live ticket, and what's out of scope.

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort. When a ticket turns out to sit past the destination, **close it** and leave one line in **Out of scope**: the gist plus why, linking the closed ticket. It stays out of **Decisions so far**, which records only the route actually walked.

## Abandon or redraw a map

The map is done "when the way is clear and no tickets remain" — but planning efforts also die, and the skill has to say how. Three signals that a map is not going to finish:

- **The destination was wrong.** Resolutions keep pointing somewhere other than where the map points.
- **Tickets multiply faster than they close.** Watch the open-ticket count across sessions — a count that rises session over session means the fog is growing, not clearing.
- **The fog never clears.** Several sessions in, the frontier hasn't advanced toward the destination.

When one of these holds, don't limp on. **Abandon or redraw:**

1. Say plainly, to the user, that the map isn't converging and why — cite the signal.
2. Decide with the user what carries forward: the still-good decisions, and any fog worth re-charting under a corrected destination.
3. **Close the map** and its open tickets. In the map body, note it was abandoned and link the successor if there is one. A redraw is a **fresh map** with a new destination, not a resumption of this one — the same rule out-of-scope work follows.

Carrying the good decisions into a successor map is a summarise-and-link, not a copy: one line each in the new map's **Decisions so far**, linking the closed tickets that hold the detail.

## Invocation

Two modes. Either way, **resolve at most one ticket per session** (research tickets excepted — they're cheap and AFK). This is guidance, not a gate: there is no script seam to enforce it, and magito doesn't block an active human to hold a rule (ADR 0013). Honour it because one decision per session is what keeps each ticket's context small, not because something stops you.

### Chart the map

The user invokes with a loose idea.

1. **Recon.** Read what the area already does (see [Recon](#recon)) before naming anything.
2. **Name the destination.** This is a grilling — hand off: ask the user to run `/grilling`, and invoke `/domain-modeling`, to pin down what this map is finding its way to. The destination fixes the scope, so it's settled first.
3. **Map the frontier.** A second grilling, **breadth-first** this time: fan out across the whole space rather than deep on one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** — the way is already clear, the journey small enough for one session — you don't need a map. Stop and ask the user how they'd like to proceed.
4. **Create the map** (marked per the Wayfinding-operations section): Destination, Notes, and the Recon brief filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**.
5. **Create the tickets you can specify now** as children of the map — then wire blocking edges in a **second pass** (tickets need ids before they can reference each other). Everything you can't yet specify stays in the fog.
6. **Do the research tickets** you just created — resolve each `research` ticket now (they're AFK and cheap), capturing findings on a `research/<name>` branch with a pointer from the ticket. Research runs at charting time, against the least-informed version of the map; that's the accepted trade for having facts in hand before the first decision. If a research question clearly depends on a decision not yet made, leave it blocked instead.
7. Stop — charting is one session's work; it resolves no decisions.

### Work through the map

The user invokes with a map (URL or number). A ticket is **optional** — without one, you pick the next decision, not the user.

1. Load the **map** — the low-res body, not every ticket.
2. **Choose and claim** the ticket. If the user named one, use it; otherwise take the first frontier ticket in order. Claim it before any work, then re-read the owner and yield if you lost the race (see the claim-race note).
3. **Resolve it** — zoom as needed: fetch the full body of any related or closed ticket on demand; run the recon pass for a HITL ticket; invoke the skills the `## Notes` block names; hand off to `/grilling` where the ticket is a grilling.
4. **Record the resolution:** post the answer as a resolution **comment**, **close** the ticket, and append one hard-capped line to the map's **Decisions so far**.
5. **Graduate the fog:** add newly-surfaced tickets (create-then-wire); move any fog the answer made specifiable out of **Not yet specified** into fresh tickets. If the answer reveals a ticket sits beyond the destination, **rule it out of scope**. If it invalidates other tickets, update or delete them. If the map is not converging, see [Abandon or redraw a map](#abandon-or-redraw-a-map).

Other sessions may be working unblocked tickets in parallel — expect the tracker to be edited concurrently.
