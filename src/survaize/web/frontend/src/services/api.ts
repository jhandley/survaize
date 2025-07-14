import { Questionnaire } from "../models/questionnaire";
import { log, logError } from "./logger";

// API service for interacting with the backend
export class SurvaizeApiService {
  private baseUrl = "/api";

  constructor(backendUrl?: string) {
    if (backendUrl) {
      this.baseUrl = backendUrl;
    }
  }

  // Read a questionnaire file (PDF or JSON)
  async readQuestionnaire(
    file: File,
    onProgress?: (percent: number, message: string) => void,
  ): Promise<Questionnaire> {
    log(`Reading file: ${file.name}`);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("format", file.name.endsWith(".pdf") ? "pdf" : "json");

      const response = await fetch(`${this.baseUrl}/questionnaire/read`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to read questionnaire");
      }

      const { job_id } = await response.json();
      log("Got job_id:", job_id);

      // Small delay to ensure the background task has started
      await new Promise((resolve) => setTimeout(resolve, 100));

      return await new Promise<Questionnaire>((resolve, reject) => {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const host = window.location.host;

        const wsUrl = `${protocol}://${host}/api/questionnaire/read/${job_id}`;
        log("Connecting to WebSocket:", wsUrl);

        const ws = new WebSocket(wsUrl);
        let isResolved = false;

        // Set up timeout to catch silent failures
        const timeout = setTimeout(() => {
          if (!isResolved) {
            if (ws.readyState == WebSocket.CONNECTING) {
              logError(
                "WebSocket timeout: No response received within 30 seconds",
              );
              cleanup();
              ws.close();
              reject(
                new Error(
                  "Connection timeout: No response received from server within 30 seconds",
                ),
              );
            }
          }
        }, 30000); // 30 second timeout

        // Helper function to clean up and resolve/reject
        const cleanup = () => {
          isResolved = true;
          clearTimeout(timeout);
        };

        ws.onopen = () => {
          log("WebSocket connection opened successfully");
          log("WebSocket state:", {
            readyState: ws.readyState,
            url: ws.url,
            protocol: ws.protocol,
          });
        };

        ws.onmessage = (event) => {
          log("WebSocket message received:", event.data);
          const data = JSON.parse(event.data);
          if (data.progress !== undefined && onProgress) {
            onProgress(data.progress, data.message || "");
          }
          if (data.questionnaire) {
            log("Received questionnaire data, closing WebSocket");
            cleanup();
            ws.close();
            resolve(data.questionnaire as Questionnaire);
          } else if (data.error) {
            log("Received error, closing WebSocket:", data.error);
            cleanup();
            ws.close();
            reject(new Error(data.error));
          }
        };

        ws.onerror = (error) => {
          logError("WebSocket error:", error);
          log("WebSocket state at error:", {
            readyState: ws.readyState,
            url: ws.url,
            protocol: ws.protocol,
          });
          cleanup();
          ws.close();
          reject(new Error("WebSocket connection failed"));
        };

        ws.onclose = (event) => {
          log(
            "WebSocket closed:",
            event.code,
            event.reason,
            "wasClean:",
            event.wasClean,
          );
          if (!isResolved) {
            cleanup();
            if (!event.wasClean && event.code !== 1000) {
              reject(
                new Error(
                  `WebSocket connection closed unexpectedly: ${event.code} ${event.reason}`,
                ),
              );
            } else {
              reject(
                new Error("WebSocket connection closed before receiving data"),
              );
            }
          }
        };
      });
    } catch (error) {
      logError("Error reading questionnaire:", error);
      throw error;
    }
  }

  // Save a questionnaire in specified format
  async saveQuestionnaire(
    questionnaire: Questionnaire,
    format: "json" | "cspro" | "surveysolutions",
  ): Promise<Blob> {
    log(`Saving questionnaire in ${format} format`);

    try {
      const response = await fetch(
        `${this.baseUrl}/questionnaire/save/${format}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(questionnaire),
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail ||
            `Failed to save questionnaire in ${format} format`,
        );
      }

      return await response.blob();
    } catch (error) {
      logError(`Error saving questionnaire in ${format} format:`, error);

      // Fallback to client-side generation for JSON
      if (format === "json") {
        log("Falling back to client-side JSON generation");
        const json = JSON.stringify(questionnaire, null, 2);
        return new Blob([json], { type: "application/json" });
      }

      throw error;
    }
  }
}
