import { Text } from "react-native";
import React from "react";

/**
 * Simple markdown parser for chat messages.
 * Supports: **bold**, bullet points (• and -), numbered lists, and line breaks.
 */
export function parseMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, lineIndex) => {
    const trimmed = line.trim();

    // Empty line = spacing
    if (trimmed === "") {
      elements.push(
        <Text key={`space-${lineIndex}`} style={{ fontSize: 8 }}>
          {"\n"}
        </Text>
      );
      return;
    }

    // Bullet points (• or -)
    const bulletMatch = trimmed.match(/^[•\-]\s+(.+)/);
    if (bulletMatch) {
      elements.push(
        <Text key={`line-${lineIndex}`} style={{ fontSize: 13, lineHeight: 22 }} className="text-white/85">
          {"  "}
          <Text className="text-aqua">{"•  "}</Text>
          {parseBoldInline(bulletMatch[1])}
          {"\n"}
        </Text>
      );
      return;
    }

    // Numbered lists
    const numberMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
    if (numberMatch) {
      elements.push(
        <Text key={`line-${lineIndex}`} style={{ fontSize: 13, lineHeight: 22 }} className="text-white/85">
          {"  "}
          <Text className="text-aqua font-semibold">{numberMatch[1]}.  </Text>
          {parseBoldInline(numberMatch[2])}
          {"\n"}
        </Text>
      );
      return;
    }

    // Regular line with possible bold
    elements.push(
      <Text key={`line-${lineIndex}`} style={{ fontSize: 13, lineHeight: 22 }} className="text-white/85">
        {parseBoldInline(trimmed)}
        {"\n"}
      </Text>
    );
  });

  return elements;
}

/** Parse **bold** segments within a line */
function parseBoldInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <Text key={i} className="text-white font-bold">
          {part.slice(2, -2)}
        </Text>
      );
    }
    return <Text key={i}>{part}</Text>;
  });
}
