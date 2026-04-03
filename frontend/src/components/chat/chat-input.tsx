import { View, TextInput, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";

interface ChatInputProps {
  onSend: (text: string) => void;
}

export default function ChatInput({ onSend }: ChatInputProps) {
  const [text, setText] = useState("");
  const insets = useSafeAreaInsets();

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  };

  const hasText = text.trim().length > 0;

  return (
    <View
      style={{ paddingBottom: Math.max(insets.bottom, 12) }}
      className="px-3 pt-2 bg-transparent"
    >
      <View className="flex-row items-center gap-2 bg-surface-light border border-white/8 rounded-full px-2 py-1.5">
        {/* Plus button */}
        <Pressable
          className="w-9 h-9 rounded-full bg-white/15 items-center justify-center"
          style={({ pressed }) => ({
            opacity: pressed ? 0.6 : 1,
            transform: [{ scale: pressed ? 0.9 : 1 }],
          })}
        >
          <Ionicons name="add" size={22} color="#aaa" />
        </Pressable>

        {/* Input */}
        <TextInput
          style={{ fontSize: 13 }}
          className="flex-1 text-white py-2 max-h-[120px]"
          placeholder="Ask Mentor anything..."
          placeholderTextColor="#666"
          value={text}
          onChangeText={setText}
          multiline
          onSubmitEditing={handleSend}
        />

        {/* Send button */}
        <Pressable
          onPress={handleSend}
          className={`w-10 h-10 rounded-full items-center justify-center ${
            hasText ? "bg-aqua" : "bg-aqua/30"
          }`}
          style={({ pressed }) => ({
            opacity: pressed ? 0.7 : 1,
            transform: [{ scale: pressed ? 0.9 : 1 }],
          })}
        >
          <Ionicons
            name="arrow-up"
            size={22}
            color={hasText ? "#000" : "#333"}
          />
        </Pressable>
      </View>
    </View>
  );
}
