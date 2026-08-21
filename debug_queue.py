#!/usr/bin/env python
"""
Debug script to test queue mechanism in GUI.
"""
import tkinter as tk
import threading
import time
import queue

def test_queue_mechanism():
    root = tk.Tk()
    root.withdraw()  # Hide window

    test_queue = queue.Queue()

    def update_status(msg):
        print(f"[MAIN THREAD] Status update: {msg}")

    def process_queue():
        try:
            while True:
                try:
                    msg_type, msg_data = test_queue.get_nowait()
                    print(f"[MAIN THREAD] Processing queue: {msg_type} = {msg_data}")
                    if msg_type == "status":
                        update_status(msg_data)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"[MAIN THREAD] Error in queue processing: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Reschedule
            root.after(100, process_queue)

    def background_worker():
        print("[BACKGROUND] Worker started")
        time.sleep(1)
        test_queue.put(("status", "Testing queue..."))
        print("[BACKGROUND] Put message in queue")
        time.sleep(1)
        test_queue.put(("status", "Worker done"))
        print("[BACKGROUND] Worker finished")

    # Start queue processing
    print("[MAIN] Starting queue processing")
    process_queue()  # This schedules the first call

    # Start background worker
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()
    print("[MAIN] Started background worker")

    # Run for 5 seconds then check results
    def check_results():
        print("[MAIN] Check results called")
        root.quit()

    root.after(5000, check_results)
    root.mainloop()
    print("[MAIN] Test completed")

if __name__ == "__main__":
    test_queue_mechanism()