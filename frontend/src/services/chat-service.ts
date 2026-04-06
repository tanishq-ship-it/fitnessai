import { API_BASE_URL } from "@/src/constants/api";

interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (messageId?: string) => void;
  onError: (error: Error) => void;
}

export function sendMessage(
  message: string,
  conversationId: string,
  callbacks: StreamCallbacks,
): void {
  const xhr = new XMLHttpRequest();
  let lastIndex = 0;

  xhr.open("POST", `${API_BASE_URL}/chat`);
  xhr.setRequestHeader("Content-Type", "application/json");

  // This fires progressively as chunks arrive
  xhr.onprogress = () => {
    const newData = xhr.responseText.slice(lastIndex);
    lastIndex = xhr.responseText.length;

    const lines = newData.split("\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const parsed = JSON.parse(line.slice(6));
        if (parsed.token) {
          callbacks.onToken(parsed.token);
        } else if (parsed.done) {
          callbacks.onDone(parsed.message_id);
        } else if (parsed.error) {
          callbacks.onError(new Error(parsed.error));
        }
      } catch {
        // Skip malformed JSON
      }
    }
  };

  xhr.onload = () => {
    if (xhr.status !== 200) {
      callbacks.onError(new Error(`Server error: ${xhr.status}`));
    }
  };

  xhr.onerror = () => {
    callbacks.onError(new Error("Network request failed"));
  };

  xhr.send(JSON.stringify({ message, conversation_id: conversationId }));
}
