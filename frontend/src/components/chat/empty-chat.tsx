import { View, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function EmptyChat() {
  return (
    <View className="flex-1 items-center justify-center px-8">
      <View className="w-16 h-16 rounded-full bg-aqua/10 items-center justify-center mb-5">
        <Ionicons name="fitness" size={32} color="#00D9C0" />
      </View>
      <Text className="text-white text-2xl font-bold mb-2">FitnessAI</Text>
      <Text className="text-white/50 text-base text-center leading-relaxed">
        Your personal fitness coach.{"\n"}Ask me anything about workouts, nutrition, or health.
      </Text>

      <View className="flex-row flex-wrap gap-2 mt-8 justify-center">
        {[
          "Build a workout plan",
          "Help with my diet",
          "Explain muscle groups",
          "Recovery tips",
        ].map((suggestion) => (
          <View
            key={suggestion}
            className="border border-white/10 rounded-full px-4 py-2"
          >
            <Text className="text-white/60 text-sm">{suggestion}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}
