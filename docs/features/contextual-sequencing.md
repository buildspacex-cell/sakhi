# Contextual Sequencing — Living Model of a Thread

> **Status**: Brainstorm / In Progress
> Last Updated: 2026-04-14

---

## The Core Insight

Standard sequence is just time ordering: T1 → T2 → T3.

**Contextual sequencing** is different. Each moment in a discussion carries a position across multiple dimensions simultaneously. Continuity means tracking where you are on each dimension — not just what was said when.

A "living model of a thread" is not a transcript. It is a **multi-dimensional state vector** that gets updated over time.

The goal is not to replay a conversation. It is to reconstruct *where a person is* across the dimensions that matter, so they can pick up the thread where it actually is — not from the beginning.

---

## What Dimensions Does a Discussion Carry?

Every discussion can be decomposed across roughly these axes:

### 1. Topical
What is being discussed? Core subject, sub-facets, topic drift markers. A discussion rarely stays on one subject — drift is signal, not noise.

### 2. Causal
Why is this being discussed? The triggering event, the stakes, what is driving it forward. Critical because the same topic can have completely different causal roots across sessions.

### 3. Epistemic
What does the person know, believe, assume? Certainties, uncertainties, knowledge gaps, belief updates. Often the most important dimension: "I used to think X, now I am not sure."

### 4. Decision / Resolution
Where is this going? Open questions, tentative conclusions, blocked decisions, action items. A thread's resolution state is what makes it feel live or closed.

### 5. Affective
How does the person feel about it? Emotional weight, tension, ambivalence, energy. Not therapy — just signal. Anxiety around a decision is information about the decision.

### 6. Relational
Who else is in the picture? Stakeholders, obligations to others, power dynamics, commitments made. Often drives the real constraint on a decision that looks purely logical.

### 7. Recurrence / Pattern
Has this come up before? Cross-session: is this a recurring theme? Is the position evolving? This is the longitudinal layer — what makes threads compound, not just continue.

---

## The Hard Problems

### Problem 1: Dimensional Entanglement
A single utterance often touches multiple dimensions simultaneously. *"I keep going back to this because I don't trust my own read on it"* is simultaneously epistemic (uncertainty), affective (anxiety), and recurrence (pattern). You cannot cleanly separate them — you have to tag with overlap.

### Problem 2: Implicit Transitions
The most important shifts are rarely stated explicitly. Nobody says "I have updated my epistemic state on this topic." They say "I have been thinking about this differently lately." The signal is weak but high-value. A model that only processes explicit statements misses the actual movement.

### Problem 3: Temporal Decay Without Input
A thread's dimensional state changes over time *even without new input*. A decision that was open six weeks ago may now be moot, resolved externally, or more urgent — without the user ever mentioning it. A living model needs time-awareness, not just event-driven updates.

### Problem 4: Thread Forking and Merging
Discussions split. A career thread forks into a financial thread and a values thread that then need to be tracked separately, with the fork point preserved. Threads also merge — two separate concerns converge into a single unresolved tension. Most systems cannot represent this; they flatten to chronology.

### Problem 5: Resolution Detection
Threads rarely close cleanly. Partial resolution is the norm. The model needs to represent partial resolution state — "the financial piece is settled, the values piece is still live" — not just open/closed.

---

## What the Architecture Needs

To build contextual sequencing, you need these primitives:

### Dimension Extractor
An LLM-powered pass over discussion input that tags each utterance or segment across all dimensions. Not classification — annotation with weights. One statement can score across multiple dimensions.

### Thread State Store
Not a transcript store. A persistent store of the *current dimensional state* of each thread, plus the history of transitions. The key object is:

```
Thread → {
  dimension → current_state,
  history_of_transitions → [ { from, to, trigger, timestamp } ]
}
```

### Transition Tracker
The transitions are as important as the states. "Moved from uncertain to more certain on X, then back to uncertain after Y" is the actual story. You need the delta, not just the snapshot.

### Salience Engine
Not all dimensions are equally load-bearing for every thread. A tactical work decision has high causal and decision weight, low affective weight. A relationship issue inverts that. The model needs to know which dimensions are *driving* a given thread — so when you surface it, you surface the right signal.

### Temporal Decay Model
Each dimension of each thread has a staleness function. Decision states decay faster than epistemic states. Affective states are volatile. Relational states are sticky. The model needs to know when a dimension's state is likely still valid vs. needs re-anchoring.

### Contextual Renderer
The output layer. Given a thread's dimensional state, render *where the person is* — not a replay of the conversation, but a coherent reconstruction of current position across the load-bearing dimensions. This is what gets surfaced when someone returns.

---

## What This Unlocks

The difference between sequence and contextual sequencing:

> **Sequence**: "You discussed this on March 3rd and again on March 18th."

> **Contextual sequencing**: "On March 3rd you were uncertain about the decision and the blocking issue was the relational dynamic with your co-founder. By March 18th you had more information but the values question was still open. That is where you left it."

The second version is why someone returns to a conversation. Not to re-read the transcript — to pick up the thread where it actually is, dimensionally.

---

## The Non-Obvious Implication

You do not need to solve all dimensions equally well to be valuable. The minimum viable version is probably three dimensions:

**Epistemic state + Decision state + Affective signal**

Those three, tracked with transitions across sessions, already produce contextual sequencing that nothing else does. The richer dimensional model is the moat — but the wedge is narrow and achievable.

---

## Open Questions

- How do you detect thread forking in real-time vs. retrospectively?
- What is the right granularity for a "thread"? A topic? A decision? A life area?
- How do you handle discussions where the person does not have a clear position — ambivalence as a stable state?
- Can dimensions be learned per-person (some people are high-epistemic, others are high-affective in how they process)?
- What does partial resolution look like in the data model — is it a dimension state or a meta-state on the thread?
- How do you surface a thread without it feeling like a dossier? The renderer is as much a product problem as a technical one.

---

## Notes / Brainstorm Scratchpad

*(add raw thoughts here as we go)*

