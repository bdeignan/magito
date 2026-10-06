# STE Structural Rules

## Contents

- Classify the text first
- The 53 rules by section
- The modal ladder
- Slop-to-simple substitutions
- Recurring substitutions
- Consistency pass
- Self-check
- Attribution

Structural writing rules adapted from ASD-STE100 Simplified Technical English (Issue 9),
the controlled language that aerospace and defense use for maintenance documentation. The
rules exist so that a tired, non-native reader cannot misread an instruction. They remove
the usual signs of AI-generated text as a side effect: long sentences, synonym rotation,
hedges, filler, and decorative clauses.

This file is the primary structural reference for `speaking-plainly`. For banned words and
AI-marker structures, see [anti-ai-markers.md](./anti-ai-markers.md). For semantic
pseudo-insight no word list catches, see [semantic-slop.md](./semantic-slop.md).

## Classify the text first

Every other rule depends on this classification.

| | Procedural (instructions) | Descriptive (explanations) |
|---|---|---|
| Purpose | Tell the reader what to do | Explain what a thing is or does |
| Verb form | Imperative: "Install the package." | Simple present, simple past, or simple future |
| Sentence limit | **20 words** | **25 words** |
| Unit rule | One instruction per sentence | One topic per paragraph, six sentences maximum |

Do not mix the two in one passage. A "Getting started" section is procedural. An
"Architecture" section is descriptive. A note inside a procedure is descriptive and gets
the 25-word limit.

## The 53 rules by section

### Section 1 — Words (1.1–1.14)

- **1.1–1.4** Use approved words only as their listed part of speech and approved meaning.
  Use only the approved forms of verbs and adjectives.
- **1.5, 1.8** Domain words are legal as technical nouns ("webhook", "commit", "endpoint").
  Use the technical nouns of your project or industry.
- **1.6** Use an unapproved word only when it is a technical noun or part of one.
- **1.7** Do not use technical nouns as verbs. "Send the event to the webhook", not
  "webhook the event".
- **1.9–1.10** Pick short, clear technical nouns. No regional, slang, or jargon words.
- **1.11** One item, one name. Do not call it "config" in one place and "settings" in
  another. Pick one term and keep it across the whole document.
- **1.12** Domain verbs are legal as technical verbs ("deploy", "compile", "merge"). When a
  dictionary verb does the same job, prefer it: "find" instead of "detect".
- **1.13** Do not use technical verbs as nouns. "Then deploy the service", not "do a deploy".
- **1.14** Use American English spelling.

### Section 2 — Multi-word nouns (2.1–2.2)

- **2.1** Write multi-word nouns of three words or fewer.
- **2.2** When a technical noun needs more than three words, write it in full once, then
  give a short form.

Break long noun chains with prepositions (of, on, in, for). "The timeout value for the
connection pool", not "the connection pool timeout configuration value".

### Section 3 — Verbs (3.1–3.7)

- **3.1–3.2** Use only: infinitive, imperative, simple present, simple past, simple future,
  past participle as adjective.
- **3.3** Use the past participle only as an adjective ("the cached response").
- **3.4** No complex verb constructions. No present perfect ("has completed"), no
  progressive passive ("is being rebuilt").
- **3.5** Use an "-ing" form only as a technical noun or inside one ("logging", "the
  mounting bracket"). Never use it as a verb.
- **3.6** Active voice. In descriptive text, passive is legal only when the agent is truly
  unknown. To repair an agentless passive, use "you" (the reader) or "we" as the subject.
- **3.7** Describe an action with a verb, not a noun. "Compress the file", not "perform
  compression of the file".

### Section 4 — Sentences (4.1–4.5)

- **4.1** Write short, clear sentences.
- **4.2** Do not omit words to shorten sentences. Keep articles and keep "that". This is
  the anti-terseness rule: STE means short sentences with complete grammar, not telegraph
  style. "Make sure that the file exists before you run the command", not "Ensure file
  exists before running".
- **4.3** Use a vertical list for complex text. Put a colon at the end of the lead-in.
  Start each item with an uppercase letter. An item gets a period only when it is a full
  sentence. The last item gets a period. Do not mix instructions and facts in one list.
  Do not nest lists.
- **4.4** Use connecting words between sentences on related topics ("Then", "As a result").
- **4.5** Put an article or demonstrative adjective before nouns where applicable.
  Exception: no article before a noun when an identifier follows it. "Restart pod
  web-7f9b2", not "Restart the pod web-7f9b2".

### Section 5 — Procedural writing (5.1–5.5)

- **5.1** Maximum 20 words per sentence. Warnings and cautions included.
- **5.2** One instruction per sentence, unless two actions happen at the same time. A step
  can have a second sentence for an immediate result or limit.
- **5.3** Write instructions in the imperative: "Run the migration."
- **5.4** Put a required condition before the command, divided by a comma: "If the build
  fails, read the log." Never trail a condition after the command.
- **5.5** Notes give information, never instructions or limits. A limit belongs with its
  action in the work step. Notes get the 25-word limit. The procedure must still work for a
  reader who deletes all notes.

### Section 6 — Descriptive writing (6.1–6.6)

- **6.1** Give information gradually: one new fact per sentence.
- **6.2** Use key words and phrases to give the text a logical structure.
- **6.3** Maximum 25 words per sentence.
- **6.4** Group related information in paragraphs.
- **6.5** One topic per paragraph.
- **6.6** Maximum six sentences per paragraph.

No imperative in descriptive text. Descriptions explain. Procedures instruct.

### Section 7 — Safety instructions (7.1–7.3)

- **7.1** Use a word that shows the risk level ("WARNING" for injury, "CAUTION" for damage).
- **7.2** Start with a clear command or condition.
- **7.3** Then give the risk or the possible result.

Never bury the instruction after the explanation. The pattern transfers to destructive CLI
flags, irreversible migrations, and dangerous API options.

### Section 8 — Punctuation and word count (8.1–8.7)

- **8.1** All standard punctuation is legal except the semicolon. Write two sentences
  instead.
- **8.2** Use hyphens to connect words that act as one unit.
- **8.3** Parentheses are legal for references, abbreviations, explanations, alternatives.
- **8.4** In a vertical list, the lead-in colon ends a sentence for word count. Each item
  after the colon counts as a new sentence with its own 20/25-word budget.
- **8.5** Text inside parentheses counts as one word.
- **8.6** Count as one word each: numbers, numbers with units, abbreviations, alphanumeric
  identifiers, quoted text (including backticked commands), titles, labels, proper nouns.
- **8.7** A hyphenated word counts as one word.

### Section 9 — Writing practices (9.1–9.4, GR-1 to GR-8)

- **9.1** When a word-for-word replacement does not work, restructure the sentence.
- **9.2** Use each approved word correctly: approved meaning, approved part of speech.
- **9.3** Do not build phrasal verbs. "Decrease" instead of "go down". "Configure" instead
  of "set up".
- **9.4** Keep one consistent style and terminology through the whole document.

General recommendations:

- **GR-1** Keep the conjunction "that" after verbs like "make sure" and "show".
- **GR-2** Keep the primary verb first and the tool after "with". "Fetch the URL with curl",
  not "Use curl to fetch the URL".
- **GR-3** Give pronouns clear referents.
- **GR-4** Prefer "this + noun" over bare "this".
- **GR-5** Avoid false friends.
- **GR-6** No Latin abbreviations. "e.g." becomes "for example". "i.e." becomes "that is".
  Delete "etc." and name the items instead.
- **GR-7** Use inclusive language.
- **GR-8** Use the possessive apostrophe form only when you are sure it is correct.

## The modal ladder

**Scope: agent instructions, procedures, and documentation only.** In chat replies and
explanations, softer modals are natural and can stay. This scoping matches STE's procedural
origin without making casual conversation stiff.

Approved modals: **can**, **will**, **must**.

Banned in instructional context: **should**, **would**, **may**, **might**, **could**.

| You wrote | Write instead |
|---|---|
| should (requirement) | must |
| should (recommendation) | Delete, or state as fact: "X is better because Y." |
| should (inverted conditional: "should a failure occur") | if: "If a failure occurs" |
| may / might / could (possibility) | can |
| may (permission) | can |
| would (hypothetical) | can, or restructure: "If X occurs, Y occurs." |

Why this matters for agents: a model reads "should" as optional. Write "must" or delete the
rule. "Could" weakens certainty even when describing real behavior. Write "can".

## Slop-to-simple substitutions

This table maps words that AI-generated text overuses to plain replacements. When the word
carries no fact, delete it instead of replacing it.

Entries already banned in [anti-ai-markers.md](./anti-ai-markers.md) are not repeated here.
That file bans leverage, delve, dive into, robust, comprehensive, seamless, "when it comes
to", and "it is worth noting that" outright.

| Slop | Write instead |
|---|---|
| utilize | use |
| in order to | to |
| prior to | before |
| ensure | make sure that |
| crucially | (delete — state the fact) |
| simply, just, easily, effortlessly | (delete) |
| powerful, performant | (delete, or give the measurable property) |
| functionality | function, feature |
| enables you to, allows you to | you can |
| is designed to, aims to | (delete — say what it does) |
| facilitate | help, make possible |
| in the event that | if |
| due to the fact that | because |
| as needed, as necessary | (state the condition) |
| and/or | Pick one, or write "X, or Y, or both" |
| gracefully handles | (say what it does: "retries three times, then stops") |
| out of the box | by default |
| under the hood | internally |
| blazingly fast, state-of-the-art | fast (give the number) / (delete) |
| streamline | make simpler, make faster |
| plethora, myriad | many |
| addresses the issue, tackles | corrects the fault, removes the error |

## Recurring substitutions

Common words the STE dictionary replaces. These are not bans — the STE forms are clearer.

| You wrote | Write instead |
|---|---|
| however | but |
| therefore | thus, as a result |
| since (meaning "because") | because |
| any (filler) | delete, or restructure: "if you have questions" |
| now (filler) | delete: "start the service", not "now start the service" |
| need to, have to | imperative in procedures; "it is necessary to" in descriptive text |
| perform | do |
| avoid | prevent |
| repeat | do again |
| the example below, the section above | name the target, or "the example that follows" |

## Consistency pass

Collapse synonym rotations to one term per concept (Rules 1.11, 9.4). Pick one and keep it
across the whole document:

- config / configuration / settings / options — pick one
- check / verify / confirm / ensure — pick one (or route by intent: "make sure that" to
  verify a state, "examine" to look for faults, "measure" to get a value)
- run / execute — pick one
- delete / remove / drop / destroy — pick one

## Self-check

Run these checks on every draft before delivering. This step is not optional.

1. **Sentence length.** Count words in the three longest sentences. Over the 20-word
   procedural or 25-word descriptive limit: split them. Backticked commands, numbers with
   units, and identifiers count as one word each (Rule 8.6).
2. **Banned patterns.** Search the draft for: `has been`, `have been`, `should`, `shall`,
   `however`, `therefore`, `-ing` verbs after a comma, semicolons. Fix every hit.
3. **Condition placement.** Search for every `if` and `when`. Each one must stand at the
   start of its sentence, before the command. "If the network is slow, increase the
   timeout", not "Increase the timeout if the network is slow".
4. **Synonym rotation.** Search for the verbs you did not pick in the consistency pass.
   Replace each hit with the chosen term.
5. **List mechanics.** Colon on the lead-in. Items start with an uppercase letter. No comma
   or semicolon at the end of an item. No mixed procedural and descriptive items.
6. **Paragraph size.** Maximum six sentences per paragraph (Rule 6.6).

## Attribution

This reference adapts rules from ASD-STE100 Simplified Technical English (Issue 9,
2025-01-15), paraphrased for a software context. It draws on the
[SimpleEnglish](https://github.com/AminBlg/SimpleEnglish) project's adaptation of the
standard.

This file is an unofficial aid. It is not affiliated with or endorsed by ASD or STEMG. No
tool can guarantee STE compliance. ASD-STE100 is a registered trademark of ASD. The official
standard is a free download at [asd-ste100.org](https://asd-ste100.org).
