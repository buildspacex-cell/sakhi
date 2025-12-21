export interface EmbeddingClient {
  embed(text: string): Promise<number[]>;
}

export class NullEmbeddingClient implements EmbeddingClient {
  async embed(): Promise<number[]> {
    return [];
  }
}
