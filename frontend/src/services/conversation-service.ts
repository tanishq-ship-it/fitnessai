import { API_BASE_URL } from "@/src/constants/api";
import { getValidAccessToken } from "@/src/services/auth-service";

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

async function authFetch<T>(url: string): Promise<T> {
  const token = await getValidAccessToken();
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchConversations(): Promise<Conversation[]> {
  const data = await authFetch<{ conversations: Conversation[] }>(
    `${API_BASE_URL}/conversations`
  );
  return data.conversations;
}

export async function fetchConversationMessages(
  conversationId: string
): Promise<ConversationMessage[]> {
  const data = await authFetch<{ messages: ConversationMessage[] }>(
    `${API_BASE_URL}/conversations/${conversationId}/messages`
  );
  return data.messages;
}
