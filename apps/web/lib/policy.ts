type PolicyMeta = Record<string, any> | undefined | null;

export function policyReasonToMessage(reason?: string, meta?: PolicyMeta): string | null {
  switch (reason) {
    case 'state_confidence_low':
      return "Let me listen a little longer before I nudge.";
    case 'max_suggestions_window': {
      const hours = typeof meta?.window_hours === 'number' ? meta.window_hours : null;
      if (hours && hours >= 1) {
        const rounded = hours >= 4 ? Math.round(hours) : Math.max(1, Math.ceil(hours));
        return `Let’s try the plan we just chose and check back in after about ${rounded} hour${rounded === 1 ? '' : 's'}.`;
      }
      return "Let’s give the plan we just picked a little time before adding another.";
    }
    case 'duplicate_recent':
      return "We just talked about this idea, so I’m holding the space quietly.";
    case 'phrase_confidence_low':
      return "Nothing thoughtful came up yet—I’ll keep thinking with you.";
    case 'llm_error':
      return "I hit a snag drafting a suggestion. Mind giving me another beat?";
    case 'empty_phrase':
      return "I’m here with you, just letting this sit for a moment.";
    default:
      if (meta?.skipped) {
        return "I’m staying quiet here so we can sit with it together.";
      }
      return null;
  }
}
