import { MissionEvent } from '../types';
import { getWebSocketUrl } from '../config';

export class MissionSocketClient {
  private eventWs: WebSocket | null = null;
  private streamWs: WebSocket | null = null;

  connectEvents(
    missionId: string,
    onEvent: (event: MissionEvent) => void,
    onError?: () => void
  ) {
    if (this.eventWs) {
      this.eventWs.close();
    }
    const url = getWebSocketUrl(`/ws/missions/${missionId}`);
    this.eventWs = new WebSocket(url);

    this.eventWs.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        onEvent(data);
      } catch (err) {
        console.error('Failed to parse websocket event', err);
      }
    };

    this.eventWs.onerror = () => {
      if (onError) onError();
    };
  }

  connectStream(
    missionId: string,
    onFrame: (base64Image: string) => void
  ) {
    if (this.streamWs) {
      this.streamWs.close();
    }
    const url = getWebSocketUrl(`/ws/stream/${missionId}`);
    this.streamWs = new WebSocket(url);

    this.streamWs.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        if (payload.type === 'screencast_frame' && payload.data) {
          onFrame(payload.data);
        }
      } catch (err) {
        console.error('Failed to parse screencast frame', err);
      }
    };
  }

  disconnectAll() {
    if (this.eventWs) {
      this.eventWs.close();
      this.eventWs = null;
    }
    if (this.streamWs) {
      this.streamWs.close();
      this.streamWs = null;
    }
  }
}
