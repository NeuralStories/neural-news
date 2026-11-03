export interface FlowDownloadRequest {
  base64: string;
  mimeType: string;
  filename: string;
}

export interface FlowMedia {
  mediaId: string;
  base64: string;
  mimeType: string;
  name?: string;
}

export interface FlowImageResult {
  mediaId: string;
  base64: string;
  mimeType: string;
}

export interface FlowVideoResult {
  base64: string;
  mimeType: string;
}

export declare const Flow: {
  media: { select(options?: { filter?: string }): Promise<FlowMedia> };
  generate: {
    image(options: Record<string, unknown>): Promise<FlowImageResult>;
    video(options: Record<string, unknown>): Promise<FlowVideoResult>;
  };
  download(request: FlowDownloadRequest): Promise<void>;
};
