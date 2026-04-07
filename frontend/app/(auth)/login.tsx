import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import AuroraBackground from "@/src/components/ui/aurora-background";
import { useAuth } from "@/src/contexts/auth-context";

export default function LoginScreen() {
  const { signIn } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length >= 8;

  async function handleSignIn() {
    if (!canSubmit || loading) return;
    setError("");
    setLoading(true);
    try {
      await signIn(email.trim(), password);
    } catch (e: any) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="flex-1 bg-black">
      <AuroraBackground />
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
      >
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            justifyContent: "center",
            paddingTop: insets.top,
            paddingBottom: insets.bottom,
          }}
          keyboardShouldPersistTaps="handled"
        >
          <View className="px-8">
            {/* Logo */}
            <View className="items-center mb-10">
              <View className="w-16 h-16 rounded-full bg-aqua/10 items-center justify-center mb-5">
                <Ionicons name="fitness" size={32} color="#00D9C0" />
              </View>
              <Text className="text-white text-3xl font-extrabold tracking-tight mb-1">
                Welcome Back
              </Text>
              <Text className="text-white/50 text-base">
                Sign in to continue
              </Text>
            </View>

            {/* Email */}
            <View className="mb-4">
              <TextInput
                className="bg-surface-light rounded-xl px-4 py-3.5 text-white text-base border border-white/8"
                placeholder="Email address"
                placeholderTextColor="rgba(255,255,255,0.3)"
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                value={email}
                onChangeText={setEmail}
                editable={!loading}
              />
            </View>

            {/* Password */}
            <View className="mb-4">
              <View className="relative">
                <TextInput
                  className="bg-surface-light rounded-xl px-4 py-3.5 text-white text-base border border-white/8 pr-12"
                  placeholder="Password"
                  placeholderTextColor="rgba(255,255,255,0.3)"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  autoComplete="password"
                  value={password}
                  onChangeText={setPassword}
                  editable={!loading}
                  onSubmitEditing={handleSignIn}
                />
                <Pressable
                  className="absolute right-3 top-0 bottom-0 justify-center"
                  onPress={() => setShowPassword(!showPassword)}
                >
                  <Ionicons
                    name={showPassword ? "eye-off-outline" : "eye-outline"}
                    size={20}
                    color="rgba(255,255,255,0.4)"
                  />
                </Pressable>
              </View>
            </View>

            {/* Error */}
            {error ? (
              <Text className="text-red-400 text-sm mb-4">{error}</Text>
            ) : null}

            {/* Sign In Button */}
            <Pressable
              className={`rounded-full py-3.5 items-center mt-2 ${
                canSubmit && !loading ? "bg-aqua" : "bg-aqua/30"
              }`}
              onPress={handleSignIn}
              disabled={!canSubmit || loading}
              style={({ pressed }) => ({
                transform: [{ scale: pressed && canSubmit ? 0.97 : 1 }],
              })}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#000" />
              ) : (
                <Text className="text-black font-bold text-base">Sign In</Text>
              )}
            </Pressable>

            {/* Sign Up Link */}
            <View className="flex-row justify-center mt-8">
              <Text className="text-white/50 text-sm">
                Don't have an account?{" "}
              </Text>
              <Pressable onPress={() => router.push("/(auth)/signup")}>
                <Text className="text-aqua text-sm font-semibold">
                  Sign Up
                </Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
