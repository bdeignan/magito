# LLM Voice and Anti-AI Writing Guidelines

Avoid standard AI writing markers, structures, and phrasing to keep the voice natural and direct.

## Banned Words
Never use these words:
delve, dive into, navigate (figurative), underscore (figurative), bolster, foster, harness (figurative: a literal test/wire harness is fine), leverage (figurative: the noun sense like highest-leverage is fine), unpack (figurative: unpacking an archive or tuple is fine), shed light on, pave the way, pivotal, groundbreaking, cutting-edge, transformative, game-changing, innovative, robust, comprehensive, seamless, intricate, nuanced (as empty praise), vibrant, multifaceted, holistic, testament, landscape (figurative), realm, utilize, facilitate, streamline, plethora, myriad, effortlessly, seamlessly, crucially, blazingly, state-of-the-art, powerful (as empty praise), performant, ensure (write *make sure that*), functionality (write *function* or *feature*)

## Banned Phrases
Never use these phrases:
- "In today's [fast-paced/rapidly evolving/digital] world..."
- "It's important/worth noting that..."
- "One of the most [important/significant/crucial]..."
- "When it comes to..." / "At its core..." / "At the end of the day..."
- "This is where X comes in" / "Let's break it down"
- "Plays a crucial role in..." / "It cannot be overstated..."
- "...underscoring the importance of..." / "...highlighting the need for..."
- "...reflecting a broader trend toward..." / "...marking a significant shift in..."
- "In order to..." (write *to*)
- "Prior to..." (write *before*)
- "In the event that..." (write *if*)
- "Due to the fact that..." (write *because*)
- "Enables you to..." / "Allows you to..." (write *you can*)
- "Is designed to..." / "Aims to..." (say what it does)
- "Gracefully handles..." (say what it does)
- "Out of the box" (write *by default*)
- "Under the hood" (write *internally*)
- "Addresses the issue..." (name the correction)

## Banned Structures
- "It's not just X — it's Y"
- "Not only X, but Y"
- "This isn't about X. It's about Y."
- "No X. No Y. Just Z."

## Dense noun and adjective stacks
Do not stack heavy compound nouns or hyphenated adjectives. "Child-prose assembly, union-grounding, and fallback propagation behind one call" is short but unreadable — unpack it into plain verbs and nouns across separate sentences. Meaning-per-word is not the goal; a reader who understands on the first pass is. A terseness instruction means cut filler, never compress meaning into a jargon stack.

## Structure & Style
- Vary sentence and paragraph lengths. Do not write uniform blocks.
- Never use "Bold term: explanation sentence" lists.
- Do not signpost ("Let's explore", "Now let's turn to"). Make the point directly.
- Do not use contractions. Write full forms (*it is*, *do not*, *will not*).
- Limit em dashes to a maximum of one per response. Use commas or parentheses instead.
- Drop performative enthusiasm ("exciting", "incredible", "powerful") and unsolicited caveats ("the honest caveat").

## Modal ladder (instructions, procedures, and documentation)

This applies to agent instructions, procedures, and documentation. It does not apply to conversational chat replies.

Approved modals: *can*, *will*, *must*. Banned in instructional context: *should*, *would*, *may*, *might*, *could*.

| You wrote | Write instead |
|---|---|
| should (requirement) | must |
| should (recommendation) | Delete, or state as fact |
| should (inverted conditional) | if |
| may / might / could (possibility) | can |
| may (permission) | can |
| would (hypothetical) | can, or restructure |

Models read "should" as optional. In a procedure or instruction, that ambiguity is a bug.

## Substitutions

Plain replacements for AI-overused words and filler. If the word carries no fact, delete it.

| Slop | Write instead |
|---|---|
| however | but |
| therefore | thus, as a result |
| since (= because) | because (keep *since* for time) |
| perform | do |
| simply, just, easily | delete the filler |
| as needed, as necessary | state the condition |
| and/or | pick one, or write "X, or Y, or both" |
| e.g. / i.e. / etc. | for example / that is / name the items |
