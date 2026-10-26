/**
 * Day 31: Ingesting Real-Time Market (RTM) Streams
 * Demonstrates resilient asynchronous polling, exponential back-off, 
 * and negative pricing validation for 5-minute ERCOT/PJM telemetry.
 */

interface RTMTickPayload {
    nodeId: string;
    timestamp: string;
    lmp: number; // Signed float to support negative pricing
    zone: string;
}

export class RTMPollingService {
    private maxRetries: number = 3;
    private baseDelayMs: number = 500;

    /**
     * Simulates fetching real-time telemetry from an ISO endpoint with back-off retry logic.
     */
    public async fetchTelemetryWithRetry(endpointUrl: string): Promise<RTMTickPayload[]> {
        let attempt = 0;

        while (attempt < this.maxRetries) {
            try {
                attempt++;
                console.log(`[*] Polling RTM endpoint (Attempt ${attempt}/${this.maxRetries}): ${endpointUrl}`);
                
                // Simulate network call or upstream ISO API response
                const rawData = await this.simulateExternalISOApiCall();
                
                // Validate and sanitize payload
                return this.validateAndSanitizePayload(rawData);

            } catch (error: any) {
                console.warn(`[!] Warning: Polling failed (${error.message}). Retrying...`);
                if (attempt >= this.maxRetries) {
                    throw new Error(`[X] Critical: RTM ingestion failed after ${this.maxRetries} attempts.`);
                }
                
                // Exponential back-off with jitter
                const delay = Math.pow(2, attempt) * this.baseDelayMs + Math.random() * 100;
                await new Promise((resolve) => setTimeout(resolve, delay));
            }
        }
        return [];
    }

    private async simulateExternalISOApiCall(): Promise<any[]> {
        // Simulate occasional random network timeout for demonstration
        if (Math.random() < 0.2) {
            throw new Error("HTTP 504 Gateway Timeout");
        }

        // Mock 5-minute RTM tick payload including negative pricing (wind over-generation)
        return [
            { nodeId: "1001", timestamp: new Date().toISOString(), lmp: 34.50, zone: "HB_NORTH" },
            { nodeId: "1002", timestamp: new Date().toISOString(), lmp: -12.75, zone: "HB_WEST" }, // Negative price!
            { nodeId: "1003", timestamp: new Date().toISOString(), lmp: 89.20, zone: "HB_HOUSTON" }
        ];
    }

    private validateAndSanitizePayload(data: any[]): RTMTickPayload[] {
        return data.map(item => {
            // Ensure lmp is parsed as a signed float (permitting negative market prices)
            const lmp = parseFloat(item.lmp);
            if (isNaN(lmp)) {
                throw new Error(`Invalid LMP format received for node ${item.nodeId}`);
            }

            return {
                nodeId: String(item.nodeId),
                timestamp: item.timestamp,
                lmp: lmp,
                zone: String(item.zone)
            };
        });
    }
}

// Execution test harness
if (require.main === module) {
    (async () => {
        console.log("=".repeat(70));
        console.log(" ⚡ HOUSTON TRADING INFRASTRUCTURE: RTM INGESTION DAEMON");
        console.log("=".repeat(70));

        // const service = RTMPollingService(); // Simulated instance
        const rtmService = new RTMPollingService();
        
        try {
            const ticks = await rtmService.fetchTelemetryWithRetry("https://api.mock-iso.org/v1/rtm/5min");
            console.log("\n[+] Successfully ingested RTM telemetry ticks:");
            console.table(ticks);
        } catch (err: any) {
            console.error(err.message);
        }
    })();
}