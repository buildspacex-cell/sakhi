import { View, Text } from 'react-native';
import { Link } from 'expo-router';

export default function Index() {
  return (
    <View className="flex-1 items-center justify-center bg-white">
      <Text className="text-2xl font-semibold text-slate-900">Welcome to Sakhi</Text>
      <Text className="mt-3 text-base text-slate-600">
        Use the Journal tab to capture a new reflection.
      </Text>
      <View className="mt-6 space-y-2">
        <Link href="/soul" className="text-blue-600">
          Soul Snapshot
        </Link>
        <Link href="/soul/timeline" className="text-blue-600">
          Soul Timeline
        </Link>
        <Link href="/soul/values" className="text-blue-600">
          Values & Commitments
        </Link>
        <Link href="/soul/shadow" className="text-blue-600">
          Shadow & Light
        </Link>
        <Link href="/soul/friction" className="text-blue-600">
          Friction
        </Link>
        <Link href="/soul/insights" className="text-blue-600">
          Insights
        </Link>
        <Link href="/soul/narrative" className="text-blue-600">
          Narrative
        </Link>
        <Link href="/soul/alignment" className="text-blue-600">
          Alignment
        </Link>
      </View>
    </View>
  );
}
