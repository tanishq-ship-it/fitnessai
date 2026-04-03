import { View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

export default function AuroraBackground() {
  return (
    <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}>
      {/* Main radial-like gradient from top-left corner */}
      <LinearGradient
        colors={["#0E3D3D", "#0A2E2E", "#071E1E", "#050F0F", "#030808"]}
        locations={[0, 0.25, 0.5, 0.75, 1]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={{ position: "absolute", width: "100%", height: "100%" }}
      />

      {/* Brighter top-left glow overlay */}
      <LinearGradient
        colors={["rgba(0,217,192,0.18)", "rgba(0,217,192,0.06)", "transparent"]}
        locations={[0, 0.3, 0.7]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.8, y: 0.8 }}
        style={{ position: "absolute", width: "100%", height: "100%" }}
      />

      {/* Subtle top edge highlight */}
      <LinearGradient
        colors={["rgba(0,255,213,0.1)", "transparent"]}
        start={{ x: 0.2, y: 0 }}
        end={{ x: 0.2, y: 0.3 }}
        style={{ position: "absolute", width: "100%", height: "100%" }}
      />
    </View>
  );
}
