import { View, TextInput, Pressable, Alert, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";

import { ChatComposerPayload, ChatImageAttachment } from "@/src/types/chat";

interface ChatInputProps {
  onSend: (payload: ChatComposerPayload) => void;
}

export default function ChatInput({ onSend }: ChatInputProps) {
  const [text, setText] = useState("");
  const [selectedImage, setSelectedImage] = useState<ChatImageAttachment | null>(null);
  const insets = useSafeAreaInsets();

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed && !selectedImage) return;
    onSend({ text: trimmed, image: selectedImage });
    setText("");
    setSelectedImage(null);
  };

  const handlePickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "Permission required",
        "Allow photo library access to attach an image."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: false,
      quality: 0.6,
      base64: true,
    });

    if (result.canceled) {
      return;
    }

    const asset = result.assets[0];
    if (!asset?.base64) {
      Alert.alert("Upload failed", "Could not read the selected image.");
      return;
    }

    setSelectedImage({
      uri: asset.uri,
      dataUrl: `data:${asset.mimeType ?? "image/jpeg"};base64,${asset.base64}`,
      mimeType: asset.mimeType ?? "image/jpeg",
      width: asset.width,
      height: asset.height,
    });
  };

  const canSend = text.trim().length > 0 || !!selectedImage;

  return (
    <View
      style={{ paddingBottom: Math.max(insets.bottom, 12) }}
      className="px-3 pt-2 bg-transparent"
    >
      {selectedImage ? (
        <View className="mb-2 self-start rounded-2xl border border-white/10 bg-surface-light/90 p-2">
          <View className="flex-row items-center gap-3">
            <Image
              source={{ uri: selectedImage.uri }}
              style={{ width: 72, height: 72, borderRadius: 14 }}
              contentFit="cover"
            />
            <View className="pr-1">
              <Text className="text-white text-sm font-semibold">
                Image attached
              </Text>
              <Text className="mt-1 text-white/45 text-xs">
                Add a message or send the image directly
              </Text>
            </View>
            <Pressable
              onPress={() => setSelectedImage(null)}
              className="w-8 h-8 items-center justify-center rounded-full bg-white/10"
              style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
            >
              <Ionicons name="close" size={16} color="#fff" />
            </Pressable>
          </View>
        </View>
      ) : null}

      <View className="flex-row items-center gap-2 bg-surface-light border border-white/8 rounded-full px-2 py-1.5">
        {/* Plus button */}
        <Pressable
          onPress={handlePickImage}
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
            canSend ? "bg-aqua" : "bg-aqua/30"
          }`}
          style={({ pressed }) => ({
            opacity: pressed ? 0.7 : 1,
            transform: [{ scale: pressed ? 0.9 : 1 }],
          })}
        >
          <Ionicons
            name="arrow-up"
            size={22}
            color={canSend ? "#000" : "#333"}
          />
        </Pressable>
      </View>
    </View>
  );
}
