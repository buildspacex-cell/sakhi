import { View, Text, Pressable } from 'react-native';

export default function Journal() {
  return (
    <View className="flex-1 items-center justify-center bg-white">
      <View className="h-24 w-24 rounded-full items-center justify-center bg-black shadow-lg">
        <Text className="text-white font-semibold">Speak</Text>
      </View>
      <Pressable className="absolute bottom-10">
        <Text className="text-blue-600 underline">Type instead</Text>
      </Pressable>
    </View>
  );
}
