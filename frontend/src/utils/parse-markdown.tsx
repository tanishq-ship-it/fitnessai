import React, { Fragment, type ReactNode } from "react";
import { Platform, ScrollView, Text, View } from "react-native";
import {
  Renderer,
  useMarkdown,
  type MarkedStyles,
  type RendererInterface,
} from "react-native-marked";
import type { ViewStyle } from "react-native";

interface ChatMarkdownProps {
  content: string;
}

const BODY_FONT_SIZE = 15;
const BODY_LINE_HEIGHT = 22;

const MONO_FONT = Platform.select({
  ios: "Menlo",
  android: "monospace",
  default: "monospace",
});

const markdownStyles: MarkedStyles = {
  text: {
    color: "rgba(255, 255, 255, 0.88)",
    fontSize: BODY_FONT_SIZE,
    lineHeight: BODY_LINE_HEIGHT,
  },
  paragraph: {
    paddingVertical: 6,
  },
  strong: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  em: {
    color: "rgba(255, 255, 255, 0.88)",
    fontStyle: "italic",
  },
  link: {
    color: "#69E6DE",
    textDecorationLine: "underline",
  },
  blockquote: {
    borderLeftColor: "rgba(105, 230, 222, 0.55)",
    borderLeftWidth: 3,
    marginVertical: 8,
    paddingLeft: 12,
    opacity: 1,
  },
  h1: {
    color: "#FFFFFF",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 6,
    marginBottom: 10,
    paddingBottom: 0,
    borderBottomWidth: 0,
  },
  h2: {
    color: "#FFFFFF",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 6,
    marginBottom: 10,
    paddingBottom: 0,
    borderBottomWidth: 0,
  },
  h3: {
    color: "#FFFFFF",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 6,
    marginBottom: 8,
  },
  h4: {
    color: "#FFFFFF",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 4,
    marginBottom: 6,
  },
  h5: {
    color: "#FFFFFF",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 4,
    marginBottom: 6,
  },
  h6: {
    color: "rgba(255, 255, 255, 0.78)",
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
    marginTop: 4,
    marginBottom: 6,
  },
  codespan: {
    color: "#F8FAFC",
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    fontFamily: MONO_FONT,
    fontSize: 12,
    lineHeight: 18,
  },
  code: {
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    borderColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 14,
    borderWidth: 1,
    marginVertical: 6,
    minWidth: "100%",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  hr: {
    borderBottomColor: "rgba(255, 255, 255, 0.12)",
    borderBottomWidth: 1,
    marginVertical: 14,
  },
  list: {
    marginVertical: 6,
  },
  li: {
    color: "rgba(255, 255, 255, 0.88)",
    fontSize: BODY_FONT_SIZE,
    lineHeight: BODY_LINE_HEIGHT,
    flexShrink: 1,
  },
  image: {
    borderRadius: 14,
    marginVertical: 6,
  },
  table: {
    borderColor: "rgba(255, 255, 255, 0.12)",
    borderRadius: 14,
    borderWidth: 1,
    marginVertical: 8,
    overflow: "hidden",
  },
  tableRow: {
    backgroundColor: "rgba(255, 255, 255, 0.04)",
    flexDirection: "row",
  },
  tableCell: {
    borderColor: "rgba(255, 255, 255, 0.08)",
    borderRightWidth: 1,
    borderBottomWidth: 1,
    minWidth: 128,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
};

class ChatMarkdownRenderer extends Renderer implements RendererInterface {
  code(
    text: string,
    _language?: string,
    containerStyle?: ViewStyle,
  ): ReactNode {
    return (
      <ScrollView
        horizontal
        key={this.getKey()}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={containerStyle}
      >
        <View>
          <Text
            selectable
            style={{
              color: "#F8FAFC",
              fontFamily: MONO_FONT,
              fontSize: BODY_FONT_SIZE,
              lineHeight: 18,
            }}
          >
            {text}
          </Text>
        </View>
      </ScrollView>
    );
  }
}

const chatMarkdownRenderer = new ChatMarkdownRenderer();

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  const elements = useMarkdown(content ?? "", {
    colorScheme: "dark",
    renderer: chatMarkdownRenderer,
    styles: markdownStyles,
    theme: {
      colors: {
        text: "#FFFFFF",
        link: "#69E6DE",
        border: "rgba(255, 255, 255, 0.12)",
        code: "rgba(255, 255, 255, 0.08)",
      },
    },
  });

  return elements.map((element, index) => (
    <Fragment key={`markdown-${index}`}>{element}</Fragment>
  ));
}
