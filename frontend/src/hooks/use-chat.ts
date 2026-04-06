import { useState, useRef, useCallback } from "react";
import { Message } from "@/src/types/chat";
import { sendMessage } from "@/src/services/chat-service";

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
  const conversationId = useRef(generateId()).current;

  const send = useCallback(
    (text: string) => {
      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      // Create placeholder assistant message
      const assistantId = generateId();
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsTyping(true);

      sendMessage(text, conversationId, {
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
        onDone: (messageId) => {
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
              content:
                "Sorry, something went wrong. Please try again.",
            };
            return updated;
          });
          setIsTyping(false);
          console.error("Chat error:", error);
        },
      });
    },
    [conversationId],
  );

  return { messages, isTyping, sendMessage: send };
}
