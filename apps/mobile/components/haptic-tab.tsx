import { BottomTabBarButtonProps } from '@react-navigation/bottom-tabs';
import { PlatformPressable } from '@react-navigation/elements';

import { useAppHaptics } from '../lib/feedback/useAppHaptics';

export function HapticTab(props: BottomTabBarButtonProps) {
  const haptics = useAppHaptics();

  return (
    <PlatformPressable
      {...props}
      onPressIn={(ev) => {
        haptics.press();
        props.onPressIn?.(ev);
      }}
    />
  );
}
