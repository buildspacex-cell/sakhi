import { Stack } from "expo-router";
import { View, Text, FlatList } from "react-native";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function AlignmentScreen() {
  const { data } = useSWR("/v1/alignment/today?person_id=me", fetcher, {
    revalidateOnFocus: false,
  });
  const map = data?.data?.alignment_map || {};

  return (
    <View style={{ flex: 1, padding: 16, backgroundColor: "#f8fafc" }}>
      <Stack.Screen options={{ title: "Daily Alignment" }} />
      <Text style={{ fontSize: 20, fontWeight: "600", marginBottom: 8 }}>Daily Alignment</Text>
      <Text>Energy: {map.energy_profile || "n/a"}</Text>
      <Text>Focus: {map.focus_profile || "n/a"}</Text>
      <Text style={{ marginTop: 12, fontWeight: "600" }}>Recommended</Text>
      <FlatList
        data={map.recommended_actions || []}
        keyExtractor={(item: any) => item.id || item.title}
        renderItem={({ item }) => <Text style={{ fontSize: 14 }}>• {item.title}</Text>}
      />
      <Text style={{ marginTop: 12, fontWeight: "600" }}>Self-care</Text>
      <FlatList
        data={map.self_care_suggestions || []}
        keyExtractor={(item: any, idx) => `${idx}`}
        renderItem={({ item }) => <Text style={{ fontSize: 14 }}>• {item}</Text>}
      />
    </View>
  );
}

