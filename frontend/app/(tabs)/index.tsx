import { View, FlatList } from "react-native";
import { useState, useRef } from "react";
import { Message } from "@/src/types/chat";
import MessageBubble from "@/src/components/chat/message-bubble";
import ChatInput from "@/src/components/chat/chat-input";
import ChatHeader from "@/src/components/chat/chat-header";
import TypingIndicator from "@/src/components/chat/typing-indicator";
import EmptyChat from "@/src/components/chat/empty-chat";
import AuroraBackground from "@/src/components/ui/aurora-background";

const MOCK_MESSAGES: Message[] = [
  {
    id: "1",
    role: "user",
    content: "I want to build muscle but I only have 3 days a week to work out. What should I do?",
    timestamp: new Date(),
  },
  {
    id: "2",
    role: "assistant",
    content:
      "Three days a week is perfect for a full-body training split. Here's what I'd recommend:\n\n**Day 1 — Push Focus**\nBench press, overhead press, squats, tricep dips\n\n**Day 2 — Pull Focus**\nDeadlifts, barbell rows, pull-ups, bicep curls\n\n**Day 3 — Full Body**\nSquats, bench press, rows, and accessory work\n\nRest at least one day between sessions. Progressive overload is key — increase weight or reps each week.",
    timestamp: new Date(),
  },
  {
    id: "3",
    role: "user",
    content: "How much protein should I be eating daily?",
    timestamp: new Date(),
  },
  {
    id: "4",
    role: "assistant",
    content:
      "For muscle building, aim for **0.7–1g of protein per pound of body weight** daily. So if you weigh 170 lbs, target 120–170g of protein.\n\nGood sources:\n• Chicken breast — 31g per 100g\n• Eggs — 6g each\n• Greek yogurt — 15g per cup\n• Whey protein shake — 25g per scoop\n\nSpread your intake across 3–4 meals for optimal absorption.",
    timestamp: new Date(),
  },
];

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>(MOCK_MESSAGES);
  const [isTyping, setIsTyping] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const handleSend = (text: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsTyping(true);
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "This is a mock response. Once we connect the API, you'll get **real fitness advice** here!\n\nThings I can help with:\n• Workout plans\n• Nutrition guidance\n• Recovery tips\n• Form corrections",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 2000);
  };

  const renderItem = ({ item, index }: { item: Message; index: number }) => {
    const showDivider = item.role === "user" && index > 0;
    return (
      <View>
        {showDivider && (
          <View className="mx-6 my-3 h-px bg-white/5" />
        )}
        <MessageBubble message={item} />
      </View>
    );
  };

  return (
    <View className="flex-1">
      <AuroraBackground />
      <ChatHeader />

      <View className="flex-1">
        {messages.length === 0 ? (
          <EmptyChat />
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            renderItem={renderItem}
            contentContainerStyle={{ paddingTop: 12, paddingBottom: 8 }}
            onContentSizeChange={() =>
              flatListRef.current?.scrollToEnd({ animated: true })
            }
            ListFooterComponent={isTyping ? <TypingIndicator /> : null}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          />
        )}

        <ChatInput onSend={handleSend} />
      </View>
    </View>
  );
}
