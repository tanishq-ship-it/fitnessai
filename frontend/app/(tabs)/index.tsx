import { View, FlatList } from "react-native";
import { useRef } from "react";
import { Message } from "@/src/types/chat";
import { useChat } from "@/src/hooks/use-chat";
import MessageBubble from "@/src/components/chat/message-bubble";
import ChatInput from "@/src/components/chat/chat-input";
import ChatHeader from "@/src/components/chat/chat-header";
import TypingIndicator from "@/src/components/chat/typing-indicator";
import EmptyChat from "@/src/components/chat/empty-chat";
import AuroraBackground from "@/src/components/ui/aurora-background";

export default function ChatScreen() {
  const { messages, isTyping, sendMessage } = useChat();
  const flatListRef = useRef<FlatList>(null);

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

        <ChatInput onSend={sendMessage} />
      </View>
    </View>
  );
}
