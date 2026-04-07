import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";

interface Props {
  onMenuPress: () => void;
  onNewChat: () => void;
}

export default function ChatHeader({ onMenuPress, onNewChat }: Props) {
  const insets = useSafeAreaInsets();

  return (
    <View style={{ paddingTop: insets.top, zIndex: 10 }} className="bg-transparent">
      <View className="flex-row items-center justify-between px-4 py-3">
        <Pressable
          className="w-10 h-10 items-center justify-center rounded-full bg-white/5"
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
          onPress={onMenuPress}
        >
          <Ionicons name="menu" size={22} color="#fff" />
        </Pressable>

        <View className="flex-row items-center gap-2">
          <Text style={{ fontSize: 16 }} className="text-white font-bold tracking-tight">
            FitnessAI
          </Text>
        </View>

        <Pressable
          className="w-10 h-10 items-center justify-center rounded-full bg-white/5"
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
          onPress={onNewChat}
        >
          <Ionicons name="create-outline" size={20} color="#fff" />
        </Pressable>
      </View>
    </View>
  );
}
