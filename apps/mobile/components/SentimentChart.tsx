import { View, Text } from "react-native";
import { VictoryChart, VictoryLine, VictoryAxis } from "victory-native";

type Point = { day: string; value: number };

export default function SentimentChart({ data }: { data: Point[] }) {
  return (
    <View className="mt-6">
      <Text className="text-lg font-semibold mb-2">7-day sentiment</Text>
      <VictoryChart>
        <VictoryAxis dependentAxis />
        <VictoryAxis />
        <VictoryLine data={data} x="day" y="value" />
      </VictoryChart>
    </View>
  );
}

