import random
import threading
import time


buffer = []
buffer_size = 5
condition = threading.Condition()


def producer():
    for item in range(1, 11):
        time.sleep(random.uniform(0.2, 0.8))
        with condition:
            while len(buffer) == buffer_size:
                condition.wait()

            buffer.append(item)
            print(f"Produced: {item} | Buffer: {buffer}")
            condition.notify()


def consumer():
    for _ in range(10):
        with condition:
            while not buffer:
                condition.wait()

            item = buffer.pop(0)
            print(f"Consumed: {item} | Buffer: {buffer}")
            condition.notify()

        time.sleep(random.uniform(0.3, 1.0))


if __name__ == "__main__":
    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    print("Producer-consumer example finished.")
