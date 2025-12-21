import type { ContextRecipe, ContextBuilderInput } from "./types";

const defaultHardPins = (input: ContextBuilderInput) => {
  const pins = new Set<string>();
  pins.add(input.message.id);
  return Array.from(pins);
};

const defaultSoftPins = () => [];

export const DefaultContextRecipe: ContextRecipe = {
  workingLimit: 5,
  episodicLimit: 5,
  episodicDiversity: 0.6,
  hardPins: defaultHardPins,
  softPins: defaultSoftPins
};
