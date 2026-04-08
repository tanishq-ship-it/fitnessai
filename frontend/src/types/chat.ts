export interface ChatImageAttachment {
  uri: string;
  dataUrl: string;
  mimeType: string;
  width: number;
  height: number;
}

export interface ChatComposerPayload {
  text: string;
  image?: ChatImageAttachment | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  imageUri?: string | null;
}
