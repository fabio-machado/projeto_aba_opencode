/**
 * Offline-first sync status management using Alpine.js + LocalStorage.
 *
 * Features:
 * - Tracks online/offline/pending status
 * - Persists queued actions to LocalStorage
 * - Implements last-write-wins conflict resolution
 * - Displays sync indicator in header
 */

function syncStatus() {
    return {
        status: 'online', // 'online', 'offline', 'pending'
        pendingCount: 0,
        queueKey: 'offline_queue',

        init() {
            this.status = navigator.onLine ? 'online' : 'offline';
            this.pendingCount = this.getQueue().length;

            window.addEventListener('online', () => {
                this.status = 'pending';
                this.syncQueue();
            });

            window.addEventListener('offline', () => {
                this.status = 'offline';
            });

            // Check for pending items on load
            if (this.pendingCount > 0 && navigator.onLine) {
                this.status = 'pending';
                this.syncQueue();
            }
        },

        /**
         * Queue an action for later sync when offline.
         * @param {Object} action - { action, table_name, payload, created_at }
         */
        queueAction(action) {
            const queue = this.getQueue();
            const existingIndex = queue.findIndex(
                (item) => item.table_name === action.table_name && item.payload.id === action.payload.id
            );

            if (existingIndex >= 0) {
                // Last-write-wins: replace with newer action
                queue[existingIndex] = {
                    ...action,
                    created_at: new Date().toISOString(),
                };
            } else {
                queue.push({
                    ...action,
                    queue_id: crypto.randomUUID(),
                    created_at: new Date().toISOString(),
                    sync_status: 'pending',
                    retry_count: 0,
                });
            }

            this.saveQueue(queue);
            this.pendingCount = queue.length;
            this.status = 'pending';
        },

        /**
         * Sync queued actions to Supabase when online.
         */
        async syncQueue() {
            const queue = this.getQueue();
            if (queue.length === 0) {
                this.status = 'online';
                return;
            }

            for (let i = 0; i < queue.length; i++) {
                const item = queue[i];
                item.sync_status = 'syncing';
                this.saveQueue(queue);

                try {
                    // HTMX request to sync endpoint
                    const response = await fetch('/api/sync/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'HX-Request': 'true',
                        },
                        body: JSON.stringify(item),
                    });

                    if (response.ok) {
                        queue.splice(i, 1);
                        i--;
                    } else if (item.retry_count < 3) {
                        item.retry_count++;
                        item.sync_status = 'pending';
                    } else {
                        item.sync_status = 'failed';
                    }
                } catch (error) {
                    console.error('Sync failed:', error);
                    if (item.retry_count < 3) {
                        item.retry_count++;
                        item.sync_status = 'pending';
                    } else {
                        item.sync_status = 'failed';
                    }
                }

                this.saveQueue(queue);
                this.pendingCount = queue.length;
            }

            this.status = 'online';
        },

        /**
         * Get the offline queue from LocalStorage.
         * @returns {Array}
         */
        getQueue() {
            try {
                const data = localStorage.getItem(this.queueKey);
                return data ? JSON.parse(data) : [];
            } catch (error) {
                console.error('Failed to read offline queue:', error);
                return [];
            }
        },

        /**
         * Save the offline queue to LocalStorage.
         * @param {Array} queue
         */
        saveQueue(queue) {
            try {
                localStorage.setItem(this.queueKey, JSON.stringify(queue));
            } catch (error) {
                console.error('Failed to save offline queue:', error);
            }
        },
    };
}
