# FitnessAI LLM Coaching Implementation Plan

## Objective

Upgrade the chat system from a single-prompt assistant into a structured coaching engine that:

- responds briefly by default
- asks short clarifying questions only when needed
- remembers the user over time
- silently turns free-form chat into structured coaching data
- retrieves relevant long-term context through Mem0 and graph relations
- generates coaching artifacts such as plans, targets, and summaries
- supports proactive coaching follow-ups over time

## Why This Change Is Needed

The current backend sends a flat system prompt plus the full conversation history into one streamed LLM call. That causes four problems:

1. Responses become too long.
2. Clarifying questions are inconsistent and often not selective enough.
3. Useful structured fitness data is not captured as first-class application data.
4. Memory retrieval is broad and not optimized for different coaching needs.

The goal is to separate these responsibilities:

- planning the reply
- building context
- generating the visible reply
- extracting structured facts and events
- storing durable memory

## Target Outcomes

After implementation, the assistant should:

- answer most normal chats in a short coach-like style
- ask at most one follow-up question when missing information blocks personalization or safety
- avoid asking for information already known from chat history, memory, graph relations, or profile state
- log workouts, meals, recovery, adherence, and progress in the background
- maintain a durable user profile across conversations
- use Mem0 for semantic recall and graph memory for durable relationships
- generate training and nutrition artifacts using dedicated prompts instead of the normal chat prompt
- detect patterns and prepare proactive follow-up tasks

## Architecture

### 1. Planner

A lightweight structured step decides:

- user intent
- response mode
- whether clarification is needed
- which single question has the highest information value
- what can be logged from the message

### 2. Context Builder

Build a compact prompt context from:

- recent chat turns
- conversation summary
- user profile
- recent structured events
- filtered Mem0 memories
- relevant graph relations
- image analysis when present

### 3. Response Generator

Generate the user-facing answer with strict style rules:

- short by default
- phone-friendly formatting
- answer first when safe defaults are possible
- ask one short question only when required

### 4. Background Extraction

After the response is generated:

- update the structured user profile
- store structured logs
- write stable facts into Mem0
- write or enrich graph relations
- refresh the conversation summary

## Storage Strategy

### Postgres

Postgres remains the source of truth for application data:

- user coaching profile
- structured events
- artifacts
- follow-up state
- proactive tasks
- coaching metrics

### Mem0

Mem0 is used for:

- semantic recall
- compact long-term memory
- memory categories and metadata filters
- reranked retrieval when higher precision is needed

### Graph

Graph memory is used for durable relationships such as:

- goals
- injuries and limitations
- diet preferences
- equipment access
- schedule habits
- repeated struggles
- coaching tactics that worked
- geography when explicitly known

For rich event history, event nodes are preferred over overloading relationships with many properties.

## Phases

## Phase 1: Response Control

Implement:

- prompt split into separate modules
- bounded recent-history window
- short-response rules
- one-question clarification planner
- response token caps by mode

Outcome:

- much shorter replies
- fewer unnecessary questions
- better token discipline

## Phase 2: Structured Coaching State

Implement:

- user coaching profile table
- coaching events table
- artifact table
- follow-up state table
- extraction pipeline for workouts, meals, recovery, adherence, progress, and profile updates

Outcome:

- silent logging from free-form chat
- durable structured user understanding

## Phase 3: Smarter Retrieval

Implement:

- memory categories and metadata filters
- reranking support
- graph-aware context building
- retrieval strategies by intent

Outcome:

- more relevant context
- fewer repeated questions
- better personalization without prompt bloat

## Phase 4: Artifact Generation

Implement dedicated artifact generation for:

- training plans
- calorie and macro targets
- weekly focus
- progress summaries
- updated phase plans

Outcome:

- plans generated through specialized prompts instead of general chat behavior

## Phase 5: Proactive Coaching

Implement:

- missed-session tracking
- silence check-in eligibility
- repeated-pattern detection
- follow-up task creation

Outcome:

- the coach can initiate meaningful follow-up logic instead of only reacting

## Phase 6: Metrics and Verification

Implement:

- prompt and completion token tracking
- planner decision tracking
- clarification frequency tracking
- memory retrieval diagnostics
- basic verification commands and smoke tests

Outcome:

- measurable quality improvements and safer iteration

## Guardrails

- Do not ask multiple profile questions in a single turn unless the user explicitly requests setup.
- Do not ask for details already known in memory, profile, graph, or recent chat.
- Do not store uncertain facts as durable memory.
- Default to safe generalized guidance when personalization is not blocked.
- Keep the normal chat path simple; use dedicated prompts for extraction and artifacts.

## Repo Change Summary

Expected main changes:

- `backend/llm.py` becomes orchestration helpers instead of one large prompt file
- new prompt modules under `backend/prompts/`
- new orchestration and retrieval services
- new Postgres tables created from backend startup
- `backend/routes.py` uses a planning and context-building pipeline before response generation

## Delivery Strategy

Implementation will proceed phase by phase in this order:

1. response control
2. structured state
3. retrieval improvements
4. artifact generation
5. proactive coaching
6. metrics and verification

This order improves user-visible behavior early, while keeping the internals modular enough to support the later phases cleanly.
