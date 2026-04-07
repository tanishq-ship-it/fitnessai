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

export default function SignupScreen() {
  const { signUp } = useAuth();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const passwordValid = password.length >= 8;
  const passwordsMatch = password === confirmPassword;
  const canSubmit = emailValid && passwordValid && passwordsMatch;

  async function handleSignUp() {
    if (!canSubmit || loading) return;

    if (!emailValid) return setError("Enter a valid email address");
    if (!passwordValid) return setError("Password must be at least 8 characters");
    if (!passwordsMatch) return setError("Passwords don't match");

    setError("");
    setLoading(true);
    try {
      await signUp(email.trim(), password);
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
                Create Account
              </Text>
              <Text className="text-white/50 text-base">
                Start your fitness journey
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
              {email.length > 0 && !emailValid && (
                <Text className="text-red-400 text-xs mt-1 ml-1">
                  Enter a valid email
                </Text>
              )}
            </View>

            {/* Password */}
            <View className="mb-4">
              <View className="relative">
                <TextInput
                  className="bg-surface-light rounded-xl px-4 py-3.5 text-white text-base border border-white/8 pr-12"
                  placeholder="Password (min 8 characters)"
                  placeholderTextColor="rgba(255,255,255,0.3)"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                  value={password}
                  onChangeText={setPassword}
                  editable={!loading}
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
              {password.length > 0 && !passwordValid && (
                <Text className="text-red-400 text-xs mt-1 ml-1">
                  At least 8 characters
                </Text>
              )}
            </View>

            {/* Confirm Password */}
            <View className="mb-4">
              <TextInput
                className="bg-surface-light rounded-xl px-4 py-3.5 text-white text-base border border-white/8"
                placeholder="Confirm password"
                placeholderTextColor="rgba(255,255,255,0.3)"
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                editable={!loading}
                onSubmitEditing={handleSignUp}
              />
              {confirmPassword.length > 0 && !passwordsMatch && (
                <Text className="text-red-400 text-xs mt-1 ml-1">
                  Passwords don't match
                </Text>
              )}
            </View>

            {/* Error */}
            {error ? (
              <Text className="text-red-400 text-sm mb-4">{error}</Text>
            ) : null}

            {/* Create Account Button */}
            <Pressable
              className={`rounded-full py-3.5 items-center mt-2 ${
                canSubmit && !loading ? "bg-aqua" : "bg-aqua/30"
              }`}
              onPress={handleSignUp}
              disabled={!canSubmit || loading}
              style={({ pressed }) => ({
                transform: [{ scale: pressed && canSubmit ? 0.97 : 1 }],
              })}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#000" />
              ) : (
                <Text className="text-black font-bold text-base">
                  Create Account
                </Text>
              )}
            </Pressable>

            {/* Sign In Link */}
            <View className="flex-row justify-center mt-8">
              <Text className="text-white/50 text-sm">
                Already have an account?{" "}
              </Text>
              <Pressable onPress={() => router.back()}>
                <Text className="text-aqua text-sm font-semibold">
                  Sign In
                </Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
