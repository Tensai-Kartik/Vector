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
      this.closeSocket(this.eventWs);
      this.eventWs = null;
    }
    const url = getWebSocketUrl(`/ws/missions/${missionId}`);
    try {
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
    } catch (e) {
      // Graceful fallback
    }
  }

  connectStream(
    missionId: string,
    onFrame: (base64Image: string) => void
  ) {
    if (this.streamWs) {
      this.closeSocket(this.streamWs);
      this.streamWs = null;
    }
    const url = getWebSocketUrl(`/ws/stream/${missionId}`);
    try {
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

      this.streamWs.onerror = () => {
        // Suppress unhandled stream socket errors on quick disconnects
      };
    } catch (e) {
      // Graceful fallback
    }
  }

  private closeSocket(ws: WebSocket) {
    try {
      ws.onerror = null;
      ws.onclose = null;
      ws.onmessage = null;
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'Normal Closure');
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => {
          try {
            ws.close(1000, 'Normal Closure');
          } catch (_) {}
        };
      }
    } catch (_) {}
  }

  disconnectAll() {
    if (this.eventWs) {
      this.closeSocket(this.eventWs);
      this.eventWs = null;
    }
    if (this.streamWs) {
      this.closeSocket(this.streamWs);
      this.streamWs = null;
    }
  }
}
