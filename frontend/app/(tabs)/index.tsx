import { View, FlatList, ActivityIndicator } from "react-native";
import { useRef, useState, useCallback } from "react";
import Animated, {
  useAnimatedKeyboard,
  useAnimatedStyle,
  KeyboardState,
} from "react-native-reanimated";
import { Message } from "@/src/types/chat";
import { useChat } from "@/src/hooks/use-chat";
import MessageBubble from "@/src/components/chat/message-bubble";
import ChatInput from "@/src/components/chat/chat-input";
import ChatHeader from "@/src/components/chat/chat-header";
import TypingIndicator from "@/src/components/chat/typing-indicator";
import EmptyChat from "@/src/components/chat/empty-chat";
import AuroraBackground from "@/src/components/ui/aurora-background";
import ConversationDrawer from "@/src/components/chat/conversation-drawer";

const AnimatedFlatList = Animated.createAnimatedComponent(FlatList<Message>);

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
  const flatListRef = useRef<FlatList<Message>>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Hook into native keyboard animation — gives exact height in real time
  const keyboard = useAnimatedKeyboard();

  // Push the entire chat + input area up by exactly the keyboard height
  const animatedContainerStyle = useAnimatedStyle(() => ({
    marginBottom: keyboard.height.value,
  }));

  const scrollToEnd = useCallback(() => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, []);

  const handleSend = useCallback(
    (payload: Parameters<typeof sendMessage>[0]) => {
      sendMessage(payload);
      scrollToEnd();
    },
    [sendMessage, scrollToEnd]
  );

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

      <Animated.View style={[{ flex: 1 }, animatedContainerStyle]}>
        {isLoadingHistory ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator size="large" color="#00D9C0" />
          </View>
        ) : messages.length === 0 ? (
          <EmptyChat onSuggestionPress={(text) => handleSend({ text })} />
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
            onLayout={() =>
              flatListRef.current?.scrollToEnd({ animated: false })
            }
            ListFooterComponent={isTyping ? <TypingIndicator /> : null}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="interactive"
          />
        )}

        <ChatInput onSend={handleSend} />
      </Animated.View>

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
