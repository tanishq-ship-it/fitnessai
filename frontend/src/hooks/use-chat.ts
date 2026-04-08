import { useState, useRef, useCallback } from "react";
import { ChatComposerPayload, Message } from "@/src/types/chat";
import { sendMessage } from "@/src/services/chat-service";
import { fetchConversationMessages } from "@/src/services/conversation-service";

function generateId(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const loadConversation = useCallback(async (convId: string) => {
    conversationIdRef.current = convId;
    setConversationId(convId);
    setIsLoadingHistory(true);
    setMessages([]);
    try {
      const msgs = await fetchConversationMessages(convId);
      setMessages(
        msgs.map((m) => ({
          id: generateId(),
          role: m.role as "user" | "assistant",
          content: m.content,
          timestamp: new Date(),
        }))
      );
    } catch (e) {
      console.error("Failed to load conversation:", e);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const startNewChat = useCallback(() => {
    conversationIdRef.current = null;
    setConversationId(null);
    setMessages([]);
    setIsTyping(false);
  }, []);

  const send = useCallback(({ text, image }: ChatComposerPayload) => {
    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: text,
      timestamp: new Date(),
      imageUri: image?.uri ?? null,
    };

    const assistantMessage: Message = {
      id: generateId(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsTyping(true);

    sendMessage(text, conversationIdRef.current, image ?? null, {
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + token,
          };
          return updated;
        });
      },
      onDone: (messageId, conversationId) => {
        if (conversationId) {
          conversationIdRef.current = conversationId;
          setConversationId(conversationId);
        }
        if (messageId) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              id: messageId,
            };
            return updated;
          });
        }
        setIsTyping(false);
      },
      onError: (error) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: "Sorry, something went wrong. Please try again.",
          };
          return updated;
        });
        setIsTyping(false);
        console.error("Chat error:", error);
      },
    });
  }, []);

  return {
    messages,
    isTyping,
    isLoadingHistory,
    sendMessage: send,
    loadConversation,
    startNewChat,
    conversationId,
  };
}
