import { View, Text, Pressable } from "react-native";
import Animated, { FadeInDown, FadeIn } from "react-native-reanimated";
import LottieView from "lottie-react-native";

interface EmptyChatProps {
  onSuggestionPress?: (text: string) => void;
}

const suggestions = [
  "Build a workout plan",
  "Help with my diet",
  "Explain muscle groups",
  "Recovery tips",
];

export default function EmptyChat({ onSuggestionPress }: EmptyChatProps) {
  return (
    <View className="flex-1 items-center justify-center px-8">
      {/* Lottie icon — fade in */}
      <Animated.View
        entering={FadeIn.duration(600)}
        className="w-20 h-20 items-center justify-center mb-5"
      >
        <LottieView
          source={require("@/assets/lootie/Sweet run cycle.json")}
          autoPlay
          loop
          style={{ width: 80, height: 80 }}
        />
      </Animated.View>

      {/* Title */}
      <Animated.Text
        entering={FadeInDown.duration(500).delay(200).springify()}
        className="text-white text-2xl font-bold mb-2"
      >
        FitnessAI
      </Animated.Text>

      {/* Subtitle */}
      <Animated.Text
        entering={FadeInDown.duration(500).delay(350).springify()}
        className="text-white/50 text-base text-center leading-relaxed"
      >
        Your personal fitness coach.{"\n"}Ask me anything about workouts,
        nutrition, or health.
      </Animated.Text>

      {/* Suggestion chips — staggered */}
      <View className="flex-row flex-wrap gap-2 mt-8 justify-center">
        {suggestions.map((suggestion, i) => (
          <Animated.View
            key={suggestion}
            entering={FadeInDown.duration(400)
              .delay(500 + i * 100)
              .springify()}
          >
            <Pressable
              className="border border-white/10 rounded-full px-4 py-2 active:bg-white/5"
              onPress={() => onSuggestionPress?.(suggestion)}
            >
              <Text className="text-white/60 text-sm">{suggestion}</Text>
            </Pressable>
          </Animated.View>
        ))}
      </View>
    </View>
  );
}
