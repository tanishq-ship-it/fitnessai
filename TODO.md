# Fitness AI - Development TODO

## 1. API & Backend Service
- [x] Set up backend API server (framework choice: FastAPI / Express)
- [x] Create chat endpoint (`POST /api/chat`) to receive user messages
- [ ] Create conversation history endpoint (`GET /api/conversations`)
- [ ] Add authentication / user identification layer
- [x] Set up environment variables and config management

## 2. LLM Chatbot Integration
- [x] Integrate LLM API calls (Claude / OpenAI) into the chat service
- [x] Build request/response pipeline (user message -> LLM -> response)
- [x] Handle streaming responses for real-time chat feel
- [ ] Add error handling and retry logic for LLM calls

## 3. Prompt Engineering
- [x] Design system prompt for fitness AI persona (tone, expertise, boundaries)
- [ ] Add contextual prompt injection (user profile, goals, history)
- [ ] Build prompt templates for different interaction types (workout plans, nutrition, form checks)
- [ ] Test and iterate on prompt quality with real conversations

## 4. Front-End Chat UI
- [x] Connect React Native chat screen to backend API
- [x] Implement message send/receive flow
- [x] Add loading states and streaming text display
- [ ] Handle error states gracefully in the UI
- [ ] Store conversation state locally for offline access

## 5. Mem0 - Memory Layer (Production)
- [ ] Set up Mem0 instance (self-hosted or cloud)
- [ ] Integrate Mem0 SDK into the backend service
- [ ] Store user preferences, goals, and context after each conversation
- [ ] Retrieve relevant memories before each LLM call and inject into prompt
- [ ] Add memory management (update, delete stale memories)
- [ ] Configure Mem0 for production (persistence, scaling, API keys)

## 6. Graph DB - Long-Term Relationships
- [ ] Choose and set up Graph DB (Neo4j / similar)
- [ ] Design graph schema (User, Workout, Goal, Progress, Preference nodes + relationships)
- [ ] Build service layer to read/write graph data
- [ ] Connect Graph DB to Mem0 — enable traversal between short-term memory and long-term relationships
- [ ] Query graph for relationship-aware context (e.g., "user prefers X because of Y injury")
- [ ] Inject graph-derived context into LLM prompts alongside Mem0 memories

## 7. Memory + Graph Integration
- [ ] Define flow: User message -> fetch Mem0 memories -> traverse Graph DB -> build context -> LLM call
- [ ] Ensure Mem0 writes also update relevant Graph DB nodes/edges
- [ ] Build a unified context builder that merges Mem0 + Graph DB results
- [ ] Test end-to-end memory recall across conversations

## 8. Production Readiness
- [ ] Add logging and monitoring
- [ ] Set up database backups (Mem0 store + Graph DB)
- [ ] Rate limiting and input validation
- [ ] Deploy backend service
- [ ] End-to-end testing of full pipeline
