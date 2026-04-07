import { View, FlatList, ActivityIndicator } from "react-native";
import { useRef, useState, useCallback } from "react";
import { Message } from "@/src/types/chat";
import { useChat } from "@/src/hooks/use-chat";
import MessageBubble from "@/src/components/chat/message-bubble";
import ChatInput from "@/src/components/chat/chat-input";
import ChatHeader from "@/src/components/chat/chat-header";
import TypingIndicator from "@/src/components/chat/typing-indicator";
import EmptyChat from "@/src/components/chat/empty-chat";
import AuroraBackground from "@/src/components/ui/aurora-background";
import ConversationDrawer from "@/src/components/chat/conversation-drawer";

export default function ChatScreen() {
  const {
    messages,
    isTyping,
    isLoadingHistory,
    sendMessage,
    loadConversation,
    startNewChat,
    conversationId,
  } = useChat();
  const flatListRef = useRef<FlatList>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleSelectConversation = useCallback(
    (id: string) => {
      if (id !== conversationId) {
        loadConversation(id);
      }
    },
    [conversationId, loadConversation]
  );

  const handleNewChat = useCallback(() => {
    startNewChat();
  }, [startNewChat]);

  const renderItem = ({ item, index }: { item: Message; index: number }) => {
    const showDivider = item.role === "user" && index > 0;
    return (
      <View>
        {showDivider && <View className="mx-6 my-3 h-px bg-white/5" />}
        <MessageBubble message={item} />
      </View>
    );
  };

  return (
    <View className="flex-1">
      <AuroraBackground />
      <ChatHeader
        onMenuPress={() => setDrawerOpen(true)}
        onNewChat={handleNewChat}
      />

      <View className="flex-1">
        {isLoadingHistory ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator size="large" color="#00D9C0" />
          </View>
        ) : messages.length === 0 ? (
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

      <ConversationDrawer
        visible={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        activeConversationId={conversationId}
      />
    </View>
  );
}
