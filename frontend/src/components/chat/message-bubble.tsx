import { View, Text } from "react-native";
import Animated, { FadeInUp } from "react-native-reanimated";
import { Image } from "expo-image";
import { Message } from "@/src/types/chat";
import { ChatMarkdown } from "@/src/utils/parse-markdown";

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
        <View className="max-w-[84%] bg-surface-light rounded-2xl rounded-br-sm px-4 py-2.5">
          {message.imageUri ? (
            <Image
              source={{ uri: message.imageUri }}
              style={{ width: 220, height: 220, borderRadius: 16, marginBottom: message.content ? 10 : 0 }}
              contentFit="cover"
            />
          ) : null}
          {message.content ? (
            <Text style={{ fontSize: 12, lineHeight: 18 }} className="text-white font-semibold">
              {message.content}
            </Text>
          ) : null}
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
      <ChatMarkdown content={message.content} />
    </Animated.View>
  );
}
