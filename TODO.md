# Fitness AI - Development TODO

## 1. API & Backend Service
- [x] Set up backend API server (FastAPI with Uvicorn)
- [x] Create chat endpoint (`POST /api/chat`) with streaming SSE responses
- [x] Create conversation history endpoints (`GET /api/conversations`, `GET /api/conversations/{id}/messages`)
- [x] Add authentication layer (signup, login, logout, refresh, JWT + refresh tokens, session management)
- [x] Set up environment variables and config management (Pydantic settings, .env)

## 2. LLM Chatbot Integration
- [x] Integrate LLM API calls (OpenRouter - configurable model)
- [x] Build request/response pipeline (user message -> memory fetch -> LLM -> streaming response)
- [x] Handle streaming responses for real-time chat feel (SSE with token-by-token streaming)
- [ ] Add retry logic for LLM calls (error handling exists, but no automatic retries)

## 3. Prompt Engineering
- [x] Design system prompt for fitness AI persona (tone, expertise, boundaries)
- [x] Add contextual prompt injection (Mem0 memories + conversation history injected into prompt)
- [ ] Build prompt templates for different interaction types (workout plans, nutrition, form checks)
- [ ] Test and iterate on prompt quality with real conversations

## 4. Front-End Chat UI
- [x] Connect React Native chat screen to backend API
- [x] Implement message send/receive flow with streaming display
- [x] Add loading states, typing indicator, and streaming text display
- [x] Build conversation drawer with history list, new chat button, and conversation switching
- [x] Add markdown parsing for AI responses (bold, bullets, numbered lists)
- [x] Build premium UI with aurora background, animations (FadeInUp, typing dots, drawer slide)
- [ ] Make suggestion prompts in empty chat clickable (currently static)
- [ ] Handle error states gracefully in the UI (partial - 401 handled, needs more coverage)
- [ ] Store conversation state locally for offline access

## 5. Authentication (Front-End)
- [x] Build login screen with email/password, validation, and error display
- [x] Build signup screen with confirm password, real-time validation
- [x] Implement AuthContext with global auth state management
- [x] Secure token storage (expo-secure-store on mobile, localStorage on web)
- [x] Auto token refresh with expiry check (60s buffer) and request deduplication
- [x] Auth gate routing (unauthenticated -> login, authenticated -> chat)
- [x] Logout with token cleanup

## 6. Mem0 - Memory Layer (Production)
- [x] Set up Mem0 instance (PgVector on PostgreSQL with HNSW indexing)
- [x] Integrate Mem0 SDK into the backend service
- [x] Store user preferences, goals, and context after each conversation
- [x] Retrieve relevant memories before each LLM call and inject into prompt
- [ ] Add memory management UI (view, update, delete stale memories)
- [ ] Configure Mem0 for production (persistence, scaling, dedicated API keys)

## 7. Graph DB - Long-Term Relationships
- [ ] Choose and set up Graph DB (Neo4j / similar)
- [ ] Design graph schema (User, Workout, Goal, Progress, Preference nodes + relationships)
- [ ] Build service layer to read/write graph data
- [ ] Connect Graph DB to Mem0 — enable traversal between short-term memory and long-term relationships
- [ ] Query graph for relationship-aware context (e.g., "user prefers X because of Y injury")
- [ ] Inject graph-derived context into LLM prompts alongside Mem0 memories

## 8. Memory + Graph Integration
- [ ] Define flow: User message -> fetch Mem0 memories -> traverse Graph DB -> build context -> LLM call
- [ ] Ensure Mem0 writes also update relevant Graph DB nodes/edges
- [ ] Build a unified context builder that merges Mem0 + Graph DB results
- [ ] Test end-to-end memory recall across conversations

## 9. Production Readiness
- [ ] Add logging and monitoring
- [ ] Set up database backups (Mem0 store + Graph DB)
- [ ] Rate limiting and input validation
- [ ] Deploy backend service
- [ ] Deploy mobile app (EAS Build / app stores)
- [ ] End-to-end testing of full pipeline
