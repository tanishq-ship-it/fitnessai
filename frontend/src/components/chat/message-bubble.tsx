import { View, Text } from "react-native";
import Animated, { FadeInUp } from "react-native-reanimated";
import { Message } from "@/src/types/chat";
import { parseMarkdown } from "@/src/utils/parse-markdown";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <Animated.View
        entering={FadeInUp.duration(300).springify()}
        className="flex-row justify-end mb-2 px-4"
      >
        <View className="bg-surface-light rounded-2xl rounded-br-sm px-4 py-2.5">
          <Text style={{ fontSize: 13 }} className="text-white font-semibold leading-relaxed">
            {message.content}
          </Text>
        </View>
      </Animated.View>
    );
  }

  // AI response — parsed markdown, no bubble
  return (
    <Animated.View
      entering={FadeInUp.duration(400).springify()}
      className="mb-2 px-5 pt-3"
    >
      {parseMarkdown(message.content)}
    </Animated.View>
  );
}
