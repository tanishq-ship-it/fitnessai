import { useEffect, useState } from "react";
import {
  View,
  Text,
  Pressable,
  FlatList,
  ActivityIndicator,
  Dimensions,
} from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  runOnJS,
  Easing,
} from "react-native-reanimated";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "@/src/contexts/auth-context";
import {
  Conversation,
  fetchConversations,
} from "@/src/services/conversation-service";

const SCREEN_WIDTH = Dimensions.get("window").width;
const DRAWER_WIDTH = SCREEN_WIDTH * 0.82;

interface Props {
  visible: boolean;
  onClose: () => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
  activeConversationId: string | null;
}

export default function ConversationDrawer({
  visible,
  onClose,
  onSelectConversation,
  onNewChat,
  activeConversationId,
}: Props) {
  const insets = useSafeAreaInsets();
  const { user, signOut } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);

  const translateX = useSharedValue(-DRAWER_WIDTH);
  const overlayOpacity = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      loadConversations();
      translateX.value = withTiming(0, {
        duration: 280,
        easing: Easing.out(Easing.cubic),
      });
      overlayOpacity.value = withTiming(1, { duration: 280 });
    } else {
      translateX.value = withTiming(-DRAWER_WIDTH, {
        duration: 240,
        easing: Easing.in(Easing.cubic),
      });
      overlayOpacity.value = withTiming(0, { duration: 240 });
    }
  }, [visible]);

  async function loadConversations() {
    setLoading(true);
    try {
      const data = await fetchConversations();
      setConversations(data);
    } catch (e) {
      console.error("Failed to load conversations:", e);
    } finally {
      setLoading(false);
    }
  }

  const drawerStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
  }));

  const overlayStyle = useAnimatedStyle(() => ({
    opacity: overlayOpacity.value,
  }));

  function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  if (!visible) return null;

  return (
    <View
      style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, zIndex: 50 }}
    >
      {/* Overlay */}
      <Animated.View style={[{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }, overlayStyle]}>
        <Pressable
          style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.6)" }}
          onPress={onClose}
        />
      </Animated.View>

      {/* Drawer */}
      <Animated.View
        style={[
          {
            position: "absolute",
            top: 0,
            bottom: 0,
            left: 0,
            width: DRAWER_WIDTH,
            backgroundColor: "#0A0A0A",
            borderRightWidth: 1,
            borderRightColor: "rgba(255,255,255,0.06)",
          },
          drawerStyle,
        ]}
      >
        {/* Header */}
        <View
          style={{ paddingTop: insets.top + 8 }}
          className="px-5 pb-4 border-b border-white/6"
        >
          <View className="flex-row items-center justify-between mb-5">
            <Text className="text-white text-lg font-bold">Chats</Text>
            <Pressable
              onPress={onClose}
              className="w-8 h-8 items-center justify-center rounded-full bg-white/5"
              style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
            >
              <Ionicons name="close" size={18} color="#fff" />
            </Pressable>
          </View>

          {/* New Chat Button */}
          <Pressable
            className="flex-row items-center gap-3 bg-aqua/10 rounded-xl px-4 py-3 border border-aqua/20"
            onPress={() => {
              onNewChat();
              onClose();
            }}
            style={({ pressed }) => ({
              opacity: pressed ? 0.7 : 1,
              transform: [{ scale: pressed ? 0.98 : 1 }],
            })}
          >
            <Ionicons name="add-circle-outline" size={20} color="#00D9C0" />
            <Text className="text-aqua font-semibold text-sm">New Chat</Text>
          </Pressable>
        </View>

        {/* Conversations List */}
        {loading ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator size="small" color="#00D9C0" />
          </View>
        ) : conversations.length === 0 ? (
          <View className="flex-1 items-center justify-center px-8">
            <Ionicons
              name="chatbubbles-outline"
              size={36}
              color="rgba(255,255,255,0.15)"
            />
            <Text className="text-white/30 text-sm mt-3 text-center">
              No conversations yet.{"\n"}Start a new chat!
            </Text>
          </View>
        ) : (
          <FlatList
            data={conversations}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ paddingVertical: 8 }}
            showsVerticalScrollIndicator={false}
            renderItem={({ item }) => {
              const isActive = item.id === activeConversationId;
              return (
                <Pressable
                  className={`mx-3 px-4 py-3.5 rounded-xl mb-1 ${
                    isActive ? "bg-white/8" : ""
                  }`}
                  onPress={() => {
                    onSelectConversation(item.id);
                    onClose();
                  }}
                  style={({ pressed }) => ({
                    opacity: pressed ? 0.7 : 1,
                    backgroundColor: pressed && !isActive
                      ? "rgba(255,255,255,0.04)"
                      : isActive
                      ? "rgba(255,255,255,0.08)"
                      : "transparent",
                  })}
                >
                  <View className="flex-row items-center justify-between">
                    <View className="flex-1 mr-3">
                      <Text
                        className={`text-sm ${
                          isActive
                            ? "text-white font-semibold"
                            : "text-white/70"
                        }`}
                        numberOfLines={1}
                      >
                        {item.title}
                      </Text>
                    </View>
                    <Text className="text-white/25 text-xs">
                      {formatDate(item.updated_at)}
                    </Text>
                  </View>
                </Pressable>
              );
            }}
          />
        )}

        {/* User Footer */}
        <View
          style={{ paddingBottom: insets.bottom + 12 }}
          className="px-5 pt-3 border-t border-white/6"
        >
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3 flex-1">
              <View className="w-8 h-8 rounded-full bg-aqua/15 items-center justify-center">
                <Ionicons name="person" size={14} color="#00D9C0" />
              </View>
              <Text
                className="text-white/60 text-sm flex-1"
                numberOfLines={1}
              >
                {user?.email}
              </Text>
            </View>
            <Pressable
              onPress={signOut}
              className="w-8 h-8 items-center justify-center rounded-full bg-white/5"
              style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
            >
              <Ionicons name="log-out-outline" size={16} color="rgba(255,255,255,0.5)" />
            </Pressable>
          </View>
        </View>
      </Animated.View>
    </View>
  );
}
